import collections
import os
from collections import defaultdict
from datetime import datetime

import cv2

from config.settings import Config
from app.application.dtos import ProcessDetectionCommand, StartSessionCommand
from app.application.services.video_analysis_aggregation_service import (
    VideoAnalysisAggregationService,
)
from app.application.services.video_analysis_file_service import VideoAnalysisFileService
from app.application.services.video_analysis_ocr_service import VideoAnalysisOcrService
from app.domain.entities.analysis_frame import FrameProcessingStatus
from app.domain.entities.analysis_session import AnalysisSourceType
from app.domain.entities.detection_result import ItemWearStatus


class VideoAnalysisService:
    ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}

    def __init__(
        self,
        upload_dir: str,
        crop_dir: str,
        analyze_worker,
        ocr_engine,
        start_analysis_session_usecase,
        create_analysis_frame_usecase,
        process_detection_result_usecase,
        complete_analysis_session_usecase,
        get_analysis_session_usecase,
        fail_analysis_session_usecase,
    ):
        self.upload_dir = upload_dir
        self.crop_dir = crop_dir
        self.analyze_worker = analyze_worker
        self.ocr_engine = ocr_engine
        self.start_analysis_session_usecase = start_analysis_session_usecase
        self.create_analysis_frame_usecase = create_analysis_frame_usecase
        self.process_detection_result_usecase = process_detection_result_usecase
        self.complete_analysis_session_usecase = complete_analysis_session_usecase
        self.get_analysis_session_usecase = get_analysis_session_usecase
        self.fail_analysis_session_usecase = fail_analysis_session_usecase

        self.frame_interval_sec = Config.FRAME_INTERVAL_SEC
        self.ocr_interval_sec = Config.OCR_INTERVAL_SEC
        self.employee_no_regex = Config.EMPLOYEE_NO_REGEX
        self.employee_no_min_length = Config.EMPLOYEE_NO_MIN_LENGTH
        self.employee_no_max_length = Config.EMPLOYEE_NO_MAX_LENGTH

        self.file_service = VideoAnalysisFileService(
            upload_dir=self.upload_dir,
            crop_dir=self.crop_dir,
        )
        self.ocr_service = VideoAnalysisOcrService(
            ocr_interval_sec=self.ocr_interval_sec,
            employee_no_regex=self.employee_no_regex,
            employee_no_min_length=self.employee_no_min_length,
            employee_no_max_length=self.employee_no_max_length,
        )
        self.aggregation_service = VideoAnalysisAggregationService(
            process_detection_result_usecase=self.process_detection_result_usecase,
        )

    def execute(
        self,
        video_file,
        frame_interval_sec: int,
        requested_by: str = "desktop-client",
        video_started_at: str | None = None,
    ):
        print("[VideoAnalysis] execute 시작")

        if video_started_at:
            if isinstance(video_started_at, datetime):
                video_started_at_dt = video_started_at
            else:
                try:
                    video_started_at_dt = datetime.fromisoformat(video_started_at)
                except Exception:
                    raise ValueError(
                        "video_started_at 형식이 올바르지 않습니다. (예: 2026-03-25 14:30:00)"
                    )
        else:
            video_started_at_dt = datetime.now()

        if video_file is None:
            print("[VideoAnalysis] 실패 - 업로드 파일 없음")
            raise ValueError("업로드 파일이 없습니다.")

        original_filename = video_file.filename or ""
        if not original_filename:
            raise ValueError("파일명이 없습니다.")

        ext = os.path.splitext(original_filename)[1].lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise ValueError("지원하지 않는 영상 형식입니다.")

        saved_video_path = self.file_service.save_video_file(video_file, ext)
        cap = cv2.VideoCapture(saved_video_path)
        if not cap.isOpened():
            raise ValueError("업로드한 영상 파일을 열 수 없습니다.")

        fps = cap.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 0:
            fps = 30.0

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        frame_step = max(int(fps / 2), 1)

        start_cmd = StartSessionCommand(
            source_type=AnalysisSourceType.VIDEO_FILE,
            total_frames=total_frames,
            frame_interval_sec=frame_interval_sec,
            source_name=original_filename,
            requested_by=requested_by,
            video_started_at=video_started_at_dt,
        )
        session = self.start_analysis_session_usecase.execute(start_cmd)
        session_id = session.session_id

        minute_frame_store = defaultdict(list)
        try:
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            duration_sec = total_frames / fps if fps > 0 else 0

            is_short_video = duration_sec <= 60.0
            results_buffer = collections.defaultdict(list)

            current_chunk_start_time = 0.0
            chunk_interval = 10.0

            current_frame_no = 0
            processed_frame_count = 0

            seen_track_ids = set()
            ocr_all_identified = False
            last_cleaned_minute_bucket = None

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                current_frame_no += 1
                current_time_sec = current_frame_no / fps

                if not is_short_video and (current_time_sec - current_chunk_start_time >= chunk_interval):
                    print(
                        f"[VideoAnalysis] 60초 Chunk 집계 시작 "
                        f"({current_chunk_start_time:.1f}s ~ {current_time_sec:.1f}s)"
                    )
                    self.aggregation_service.aggregate_and_save(results_buffer)
                    results_buffer.clear()
                    current_chunk_start_time = current_time_sec

                if current_frame_no % frame_step != 0:
                    continue

                processed_frame_count += 1
                current_time_sec = current_frame_no / fps
                minute_bucket = int(current_time_sec // 60)

                if last_cleaned_minute_bucket is None:
                    last_cleaned_minute_bucket = minute_bucket
                elif minute_bucket > last_cleaned_minute_bucket:
                    self.file_service.cleanup_previous_minute_frames(
                        minute_frame_store=minute_frame_store,
                        target_minute_bucket=last_cleaned_minute_bucket,
                    )
                    last_cleaned_minute_bucket = minute_bucket

                active_persons = self.analyze_worker.run_inference_for_video(frame)
                people = list(active_persons.values())

                current_track_ids = {person.id for person in people}
                new_track_ids = current_track_ids - seen_track_ids

                if new_track_ids:
                    ocr_all_identified = False

                seen_track_ids.update(current_track_ids)

                frame_entity = self.create_analysis_frame_usecase.execute(
                    session_id=session.id,
                    frame_no=current_frame_no,
                    frame_time_sec=current_time_sec,
                    person_count=len(people),
                    frame_image_path=None,
                    processing_status=FrameProcessingStatus.PROCESSED,
                    error_message=None,
                )

                for person_index, person in enumerate(people, start=1):
                    ocr_data = None
                    crop_image_path = None

                    should_run_ocr = (
                        not ocr_all_identified
                        and self.ocr_service.should_run_ocr_for_person(person, current_time_sec)
                    )

                    if should_run_ocr:
                        crop_image_path = self.file_service.save_crop_image(
                            session_id=session_id,
                            frame_no=current_frame_no,
                            person_index=person_index,
                            crop_image=person.crop_image,
                        )

                        if crop_image_path is not None:
                            ocr_data = self.ocr_engine.extract_worker_id(person.crop_image)
                            person.last_ocr_at_sec = current_time_sec

                            self.ocr_service.apply_ocr_result_to_person(person, ocr_data)
                            self.ocr_service.register_ocr_frame_candidate(
                                minute_frame_store=minute_frame_store,
                                minute_bucket=minute_bucket,
                                person=person,
                                frame_no=current_frame_no,
                                crop_image_path=crop_image_path,
                            )

                    cmd = ProcessDetectionCommand(
                        session_id=session_id,
                        frame_id=frame_entity.id,
                        person_index=person_index,
                        helmet_status=(
                            ItemWearStatus.WEARING
                            if person.has_helmet
                            else ItemWearStatus.NOT_WEARING
                        ),
                        vest_status=(
                            ItemWearStatus.WEARING
                            if person.has_vest
                            else ItemWearStatus.NOT_WEARING
                        ),
                        employee_no=getattr(person, "employee_no", None),
                        ocr_text=(ocr_data or {}).get("raw_text"),
                        ocr_confidence=getattr(person, "ocr_confidence", None),
                        person_box_x=person.bbox[0],
                        person_box_y=person.bbox[1],
                        person_box_width=max(0, person.bbox[2] - person.bbox[0]),
                        person_box_height=max(0, person.bbox[3] - person.bbox[1]),
                        crop_image_path=crop_image_path,
                    )

                    print(
                        f"      - [FrameLog] Person {person.id}: "
                        f"Helmet={person.helmet_confidence:.2f}, "
                        f"Vest={person.vest_confidence:.2f}"
                    )

                    results_buffer[person.id].append(
                        {
                            "cmd": cmd,
                            "helmet_conf": person.helmet_confidence,
                            "vest_conf": person.vest_confidence,
                        }
                    )

                    self.process_detection_result_usecase.execute(cmd)

                ocr_all_identified = (
                    len(people) > 0
                    and all(self.ocr_service.is_person_identified(person) for person in people)
                )

            cap.release()

            if last_cleaned_minute_bucket is not None:
                self.file_service.cleanup_previous_minute_frames(
                    minute_frame_store=minute_frame_store,
                    target_minute_bucket=last_cleaned_minute_bucket,
                )

            if results_buffer:
                print(
                    f"[VideoAnalysis] 최종/잔여 구간 집계 처리 시작 "
                    f"(인원수: {len(results_buffer)})"
                )
                self.aggregation_service.aggregate_and_save(results_buffer)

            self.complete_analysis_session_usecase.execute(
                session_id=session_id,
                processed_frames=processed_frame_count,
            )

            updated_session = self.get_analysis_session_usecase.execute(session_id)
            return updated_session

        except Exception as exc:
            cap.release()
            self.fail_analysis_session_usecase.execute(session_id, str(exc))
            raise
