import os
import re
import uuid
import cv2
import collections

from collections import defaultdict
from config.settings import Config
from app.application.dtos import StartSessionCommand, ProcessDetectionCommand
from app.domain.entities.analysis_session import AnalysisSourceType
from app.domain.entities.analysis_frame import FrameProcessingStatus
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

        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.crop_dir, exist_ok=True)

    def execute(self, video_file, requested_by: str = "desktop-client", frame_interval_sec: int | None = None):
        print("[VideoAnalysis] execute 시작")

        if video_file is None: 
            print("[VideoAnalysis] 실패 - 업로드 파일 없음")
            raise ValueError("업로드 파일이 없습니다.")

        original_filename = video_file.filename or ""
        if not original_filename:
            raise ValueError("파일명이 없습니다.")

        ext = os.path.splitext(original_filename)[1].lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise ValueError("지원하지 않는 영상 형식입니다.")

        saved_video_path = self._save_video_file(video_file, ext)
        cap = cv2.VideoCapture(saved_video_path)
        if not cap.isOpened():
            raise ValueError("업로드한 영상 파일을 열 수 없습니다.")

        fps = cap.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 0:
            fps = 30.0

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)


        # YOLO 처리 주기: 2fps
        frame_step = max(int(fps / 2), 1)

        start_cmd = StartSessionCommand(
            source_type=AnalysisSourceType.VIDEO_FILE,
            total_frames=total_frames,
            frame_interval_sec=frame_interval_sec,
            source_name=original_filename,
            requested_by=requested_by,
        )
        session = self.start_analysis_session_usecase.execute(start_cmd)
        session_id = session.session_id


        # 1분 구간별 OCR 저장 프레임 관리
        # { minute_bucket: [ {path, score, track_id, employee_no, frame_no}, ... ] }
        minute_frame_store = defaultdict(list)
        try:
            # 영상이 몇 프레임인 지 파악
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0 # 초당 프레임 수
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0) # 전체 프레임 수
            duration_sec = total_frames / fps if fps > 0 else 0 # 영상 길이
            
            # [Step 1 & 2] 분석 데이터 버퍼링 설정 (60초 기준)
            is_short_video = duration_sec <= 60.0
            results_buffer = collections.defaultdict(list) # person_id -> list of detection data

            # [Step 2] 60초 단위 Chunk 관리를 위한 변수
            current_chunk_start_time = 0.0
            CHUNK_INTERVAL = 10.0

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

                # [Step 2] 60초 초과 영상에 대한 Chunk 정산 처리
                if not is_short_video and (current_time_sec - current_chunk_start_time >= CHUNK_INTERVAL):
                    print(f"[VideoAnalysis] 60초 Chunk 정산 시작 ({current_chunk_start_time:.1f}s ~ {current_time_sec:.1f}s)")
                    self._aggregate_and_save(results_buffer)
                    results_buffer.clear()
                    current_chunk_start_time = current_time_sec

                if current_frame_no % frame_step != 0:
                    continue

                processed_frame_count += 1
                current_time_sec = current_frame_no / fps
                minute_bucket = int(current_time_sec // 60)

                # 이전 1분 구간 정리
                if last_cleaned_minute_bucket is None:
                    last_cleaned_minute_bucket = minute_bucket
                elif minute_bucket > last_cleaned_minute_bucket:
                    self._cleanup_previous_minute_frames(
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
                        and self._should_run_ocr_for_person(person, current_time_sec)
                    )

                    if should_run_ocr:
                        crop_image_path = self._save_crop_image(
                            session_id=session_id,
                            frame_no=current_frame_no,
                            person_index=person_index,
                            crop_image=person.crop_image,
                        )

                        if crop_image_path is not None:
                            ocr_data = self.ocr_engine.extract_worker_id(person.crop_image)
                            person.last_ocr_at_sec = current_time_sec

                            self._apply_ocr_result_to_person(person, ocr_data)

                            self._register_ocr_frame_candidate(
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
                        helmet_status=ItemWearStatus.WEARING if person.has_helmet else ItemWearStatus.NOT_WEARING,
                        vest_status=ItemWearStatus.WEARING if person.has_vest else ItemWearStatus.NOT_WEARING,
                        employee_no=getattr(person, "employee_no", None),
                        ocr_text=(ocr_data or {}).get("raw_text"),
                        ocr_confidence=getattr(person, "ocr_confidence", None),
                        person_box_x=person.bbox[0],
                        person_box_y=person.bbox[1],
                        person_box_width=max(0, person.bbox[2] - person.bbox[0]),
                        person_box_height=max(0, person.bbox[3] - person.bbox[1]),
                        crop_image_path=crop_image_path,
                    )


                    # [Log] 프레임별 신뢰도 출력
                    print(f"      - [FrameLog] Person {person.id}: Helmet={person.helmet_confidence:.2f}, Vest={person.vest_confidence:.2f}")

                    # [Step 1 / Step 2] 버퍼에 누적 (즉시 저장하지 않음)
                    results_buffer[person.id].append({
                        "cmd": cmd,
                        "helmet_conf": person.helmet_confidence,
                        "vest_conf": person.vest_confidence
                    })

                    self.process_detection_result_usecase.execute(cmd)

                ocr_all_identified = (
                    len(people) > 0
                    and all(self._is_person_identified(person) for person in people)
                )

            cap.release()

            # 마지막 남은 1분 구간도 정리
            if last_cleaned_minute_bucket is not None:
                self._cleanup_previous_minute_frames(
                    minute_frame_store=minute_frame_store,
                    target_minute_bucket=last_cleaned_minute_bucket,
                )

            # [최종 정산] 남은 데이터 처리 (짧은 영상 전체 또는 긴 영상의 마지막 자투리 Chunk)
            if results_buffer:
                print(f"[VideoAnalysis] 최종/남은 구간 정산 처리 시작 (인원수: {len(results_buffer)})")
                self._aggregate_and_save(results_buffer)

            self.complete_analysis_session_usecase.execute(
                session_id=session_id,
                processed_frames=processed_frame_count,
            )

            updated_session = self.get_analysis_session_usecase.execute(session_id)
            return updated_session

        except Exception as e:
            cap.release()
            self.fail_analysis_session_usecase.execute(session_id, str(e))
            raise


    def _aggregate_and_save(self, buffer: dict):
        """버퍼링된 프레임 데이터를 정산하여 DB에 저장합니다."""
        for p_id, frames_data in buffer.items():
            if not frames_data:
                continue
                
            avg_helmet_conf = sum(d['helmet_conf'] for d in frames_data) / len(frames_data)
            avg_vest_conf = sum(d['vest_conf'] for d in frames_data) / len(frames_data)

            # [Log] 정산 구간 평균 신뢰도 출력
            print(f"  ==> [AggregationLog] Person {p_id} (Data Count: {len(frames_data)}): "
                  f"Avg Helmet={avg_helmet_conf:.4f}, Avg Vest={avg_vest_conf:.4f}")
            
            # 신뢰도 기반 최종 판정 (0.8 이상일 때만 WEARING으로 인정)
            final_cmd = frames_data[-1]['cmd']
            final_cmd.helmet_status = ItemWearStatus.WEARING if avg_helmet_conf >= 0.7 else ItemWearStatus.NOT_WEARING
            final_cmd.vest_status = ItemWearStatus.WEARING if avg_vest_conf >= 0.7 else ItemWearStatus.NOT_WEARING
            
            self.process_detection_result_usecase.execute(final_cmd)
            print(f"[VideoAnalysis] 정산 결과 저장 완료 - Person ID: {p_id}, "
                  f"Helmet_Avg: {avg_helmet_conf:.2f}, Vest_Avg: {avg_vest_conf:.2f}")

    def _is_person_identified(self, person) -> bool:
        return bool(getattr(person, "ocr_confirmed", False) and getattr(person, "employee_no", None))

    def _should_run_ocr_for_person(self, person, current_time_sec: float) -> bool:
        if self._is_person_identified(person):
            return False

        if person.crop_image is None:
            return False

        if getattr(person.crop_image, "size", 0) == 0:
            return False

        last_ocr_at_sec = getattr(person, "last_ocr_at_sec", None)
        if last_ocr_at_sec is None:
            return True

        return (current_time_sec - last_ocr_at_sec) >= self.ocr_interval_sec

    def _apply_ocr_result_to_person(self, person, ocr_data: dict | None) -> None:
        if not ocr_data:
            return

        raw_worker_id = (ocr_data or {}).get("worker_id")
        raw_text = (ocr_data or {}).get("raw_text")
        cleaned_text = (ocr_data or {}).get("cleaned_text")
        confidence = float((ocr_data or {}).get("confidence") or 0.0)

        candidate = self._normalize_employee_no(cleaned_text or raw_worker_id or raw_text)
        if not candidate:
            return

        if not self._is_valid_employee_no(candidate):
            return

        person.ocr_candidate_counts[candidate] = person.ocr_candidate_counts.get(candidate, 0) + 1
        person.ocr_confidence = confidence

        if person.ocr_candidate_counts[candidate] >= 2:
            person.employee_no = candidate
            person.ocr_confirmed = True

    def _normalize_employee_no(self, value) -> str | None:
        if value is None:
            return None

        text = str(value).strip()
        if not text:
            return None

        return text

    def _is_valid_employee_no(self, employee_no: str) -> bool:
        if not employee_no:
            return False

        if self.employee_no_min_length > 0 and len(employee_no) < self.employee_no_min_length:
            return False

        if self.employee_no_max_length > 0 and len(employee_no) > self.employee_no_max_length:
            return False

        if self.employee_no_regex:
            return re.fullmatch(self.employee_no_regex, employee_no) is not None

        return True

    def _register_ocr_frame_candidate(
        self,
        minute_frame_store: dict,
        minute_bucket: int,
        person,
        frame_no: int,
        crop_image_path: str,
    ) -> None:
        score = self._calculate_best_frame_score(person)

        minute_frame_store[minute_bucket].append(
            {
                "path": crop_image_path,
                "score": score,
                "track_id": person.id,
                "employee_no": getattr(person, "employee_no", None),
                "frame_no": frame_no,
            }
        )

    def _calculate_best_frame_score(self, person) -> float:
        # 추후 선정 기준 교체 가능하도록 분리
        area_score = float(person.get_bbox_area()) if hasattr(person, "get_bbox_area") else 0.0
        confidence_score = float(getattr(person, "ocr_confidence", 0.0) or 0.0)

        # bbox 크기를 우선, OCR confidence를 보조 점수로 사용
        return area_score + (confidence_score * 1000.0)

    def _cleanup_previous_minute_frames(self, minute_frame_store: dict, target_minute_bucket: int) -> None:
        candidates = minute_frame_store.get(target_minute_bucket, [])
        if not candidates:
            return

        best = max(candidates, key=lambda x: x["score"])

        for item in candidates:
            path = item["path"]
            if path == best["path"]:
                continue

            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"[VideoAnalysis] OCR crop 삭제 실패 - path={path}, error={e}")

        # 정리 완료한 minute bucket은 메모리에서도 제거
        minute_frame_store.pop(target_minute_bucket, None)

    def _save_video_file(self, video_file, ext: str) -> str:
        saved_name = f"{uuid.uuid4().hex}{ext}"
        saved_path = os.path.join(self.upload_dir, saved_name)
        video_file.save(saved_path)
        return saved_path

    def _save_crop_image(self, session_id: str, frame_no: int, person_index: int, crop_image):
        if crop_image is None:
            return None

        if getattr(crop_image, "size", 0) == 0:
            return None

        filename = f"{session_id}_f{frame_no}_p{person_index}.jpg"
        saved_path = os.path.join(self.crop_dir, filename)
        cv2.imwrite(saved_path, crop_image)
        return saved_path