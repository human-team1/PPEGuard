import os
from datetime import datetime

import cv2

from config.settings import Config
from app.application.dtos import StartSessionCommand
from app.application.services.video_analysis_file_service import VideoAnalysisFileService
from app.application.services.video_analysis_ocr_service import VideoAnalysisOcrService
from app.domain.entities.analysis_session import AnalysisSourceType


class VideoAnalysisService:
    ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}

    def __init__(
        self,
        upload_dir: str,
        crop_dir: str,
        analyze_worker,
        ocr_engine,
        segment_result_service,
        realtime_event_service,
        start_analysis_session_usecase,
        complete_analysis_session_usecase,
        get_analysis_session_usecase,
        fail_analysis_session_usecase,
    ):
        self.upload_dir = upload_dir
        self.crop_dir = crop_dir
        self.analyze_worker = analyze_worker
        self.ocr_engine = ocr_engine
        self.segment_result_service = segment_result_service
        self.realtime_event_service = realtime_event_service
        self.start_analysis_session_usecase = start_analysis_session_usecase
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
                video_started_at_source = "user_input"
            else:
                try:
                    video_started_at_dt = datetime.fromisoformat(video_started_at)
                    video_started_at_source = "user_input"
                except Exception:
                    raise ValueError(
                        "video_started_at 형식이 올바르지 않습니다. (예: 2026-03-25 14:30:00)"
                    )
        else:
            video_started_at_dt = datetime.now()
            video_started_at_source = "server_now"

        print(
            "[VideoAnalysis] video_started_at resolved - "
            f"source={video_started_at_source}, value={video_started_at_dt.isoformat()}",
            flush=True,
        )

        if video_file is None:
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
        total_time_sec = total_frames / fps if fps > 0 else 0.0
        effective_frame_interval_sec = max(float(self.frame_interval_sec or 0.0), 0.0)
        effective_ocr_interval_sec = max(float(self.ocr_interval_sec or 0.0), 0.0)
        frame_step = max(int(round(fps * effective_frame_interval_sec)), 1)

        print(
            "[VideoAnalysis] interval config applied - "
            f"fps={fps:.2f}, frame_interval_sec={effective_frame_interval_sec}, "
            f"ocr_interval_sec={effective_ocr_interval_sec}, frame_step={frame_step}",
            flush=True,
        )

        start_cmd = StartSessionCommand(
            source_type=AnalysisSourceType.VIDEO_FILE,
            total_frames=total_frames,
            frame_interval_sec=max(int(round(effective_frame_interval_sec)), 1),
            source_name=original_filename,
            requested_by=requested_by,
            video_started_at=video_started_at_dt,
        )
        session = self.start_analysis_session_usecase.execute(start_cmd)
        session_id = session.session_id

        self.realtime_event_service.emit_session_status(
            session_id=session_id,
            source_type=AnalysisSourceType.VIDEO_FILE.value,
            status="started",
        )
        self.realtime_event_service.emit_session_status(
            session_id=session_id,
            source_type=AnalysisSourceType.VIDEO_FILE.value,
            status="processing",
        )

        try:
            current_frame_no = 0
            processed_frame_count = 0
            last_progress_emit_sec = -1.0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                current_frame_no += 1
                if current_frame_no != 1 and current_frame_no % frame_step != 0:
                    continue

                processed_frame_count += 1
                current_time_sec = current_frame_no / fps
                active_persons = self.analyze_worker.run_inference_for_video(frame)
                people = list(active_persons.values())

                for person in people:
                    person.latest_ocr_candidate = None
                    person.latest_ocr_regex_matched = False
                    person.latest_ocr_raw_text = None

                    if self.ocr_service.should_run_ocr_for_person(person, current_time_sec):
                        ocr_data = self.ocr_engine.extract_worker_id(person.crop_image)
                        person.last_ocr_at_sec = current_time_sec
                        self.ocr_service.apply_ocr_result_to_person(person, ocr_data)

                self.segment_result_service.ingest_frame(
                    session=session,
                    frame_no=current_frame_no,
                    frame_time_sec=current_time_sec,
                    frame=frame,
                    people=people,
                )

                if current_time_sec - last_progress_emit_sec >= 1.0 or current_frame_no == 1:
                    detections = self._build_detection_payload(people)
                    current_counts = self._build_current_counts(detections)
                    self.realtime_event_service.emit_progress(
                        session_id=session_id,
                        source_type=AnalysisSourceType.VIDEO_FILE.value,
                        current_time_sec=current_time_sec,
                        total_time_sec=total_time_sec,
                        processed_frames=processed_frame_count,
                        current_counts=current_counts,
                    )
                    self.realtime_event_service.emit_frame_result(
                        session_id=session_id,
                        source_type=AnalysisSourceType.VIDEO_FILE.value,
                        frame=frame,
                        detections=detections,
                    )
                    last_progress_emit_sec = current_time_sec

            cap.release()
            self.segment_result_service.finalize_session(session, reason="completed")

            self.complete_analysis_session_usecase.execute(
                session_id=session_id,
                processed_frames=processed_frame_count,
            )
            self.realtime_event_service.emit_session_status(
                session_id=session_id,
                source_type=AnalysisSourceType.VIDEO_FILE.value,
                status="completed",
            )

            updated_session = self.get_analysis_session_usecase.execute(session_id)
            return updated_session

        except Exception as exc:
            cap.release()
            self.segment_result_service.finalize_session(session, reason="failed")
            self.fail_analysis_session_usecase.execute(session_id, str(exc))
            self.realtime_event_service.emit_session_status(
                session_id=session_id,
                source_type=AnalysisSourceType.VIDEO_FILE.value,
                status="failed",
            )
            raise

    def _build_detection_payload(self, people: list) -> list[dict]:
        detections = []
        for person in people:
            detections.append(
                {
                    "track_id": person.id,
                    "employee_id": getattr(person, "employee_no", None),
                    "ocr_number": getattr(person, "employee_no", None),
                    "helmet_status": "WORN" if person.has_helmet else "NOT_WORN",
                    "vest_status": "WORN" if person.has_vest else "NOT_WORN",
                    "bbox": {
                        "x1": int(person.bbox[0]),
                        "y1": int(person.bbox[1]),
                        "x2": int(person.bbox[2]),
                        "y2": int(person.bbox[3]),
                    },
                }
            )
        return detections

    def _build_current_counts(self, detections: list[dict]) -> dict:
        return {
            "detected_person_count": len(detections),
            "confirmed_ocr_person_count": sum(
                1 for item in detections if item.get("ocr_number")
            ),
            "helmet_not_worn_count": sum(
                1 for item in detections if item.get("helmet_status") != "WORN"
            ),
            "vest_not_worn_count": sum(
                1 for item in detections if item.get("vest_status") != "WORN"
            ),
        }
