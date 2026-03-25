import os
import uuid
import cv2
from datetime import datetime 

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


        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.crop_dir, exist_ok=True)

    def execute(self, 
                video_file, 
                requested_by: str = "desktop-client", 
                frame_interval_sec: int = 3,
                video_started_at: str | None = None): 
        print("[VideoAnalysis] execute 시작") 

        if video_started_at:
            if isinstance(video_started_at, datetime):
                video_started_at_dt = video_started_at
            else:
                try:
                    video_started_at_dt = datetime.fromisoformat(video_started_at)
                except Exception:
                    raise ValueError("video_started_at 형식이 올바르지 않습니다. (예: 2026-03-25 14:30:00)")
        else:
            video_started_at_dt = datetime.now()

        if video_file is None:
            print("[VideoAnalysis] 실패 - 업로드 파일 없음")
            raise ValueError("업로드 파일이 없습니다.")

        original_filename = video_file.filename or ""
        if not original_filename:
            print("[VideoAnalysis] 실패 - 파일명 없음")
            raise ValueError("파일명이 없습니다.")

        print(f"[VideoAnalysis] 업로드 파일명: {original_filename}")

        ext = os.path.splitext(original_filename)[1].lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            print(f"[VideoAnalysis] 실패 - 지원하지 않는 확장자: {ext}")
            raise ValueError("지원하지 않는 영상 형식입니다.")

        saved_video_path = self._save_video_file(video_file, ext)
        print(f"[VideoAnalysis] 영상 저장 완료: {saved_video_path}")

        cap = cv2.VideoCapture(saved_video_path)
        if not cap.isOpened():
            print("[VideoAnalysis] 실패 - 영상 파일 열기 실패")
            raise ValueError("업로드한 영상 파일을 열 수 없습니다.")

        print("[VideoAnalysis] VideoCapture 오픈 완료")

        fps = cap.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 0:
            fps = 30.0
            print("[VideoAnalysis] FPS 조회 실패, 기본값 30.0 사용")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        frame_step = max(int(fps * frame_interval_sec), 1)

        print(
            f"[VideoAnalysis] 영상 정보 - fps={fps}, total_frames={total_frames}, "
            f"frame_interval_sec={frame_interval_sec}, frame_step={frame_step}"
        )

        start_cmd = StartSessionCommand(
            source_type=AnalysisSourceType.VIDEO_FILE,
            frame_interval_sec=frame_interval_sec,
            source_name=original_filename,
            requested_by=requested_by,
            video_started_at=video_started_at_dt,
        )

        session = self.start_analysis_session_usecase.execute(start_cmd)
        session_id = session.session_id
        print(f"[VideoAnalysis] 세션 생성 완료 - session_id={session_id}, session_pk={session.id}")

        try:
            current_frame_no = 0
            processed_frame_count = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    print("[VideoAnalysis] 프레임 읽기 종료 - 영상 끝")
                    break

                current_frame_no += 1

                if current_frame_no % frame_step != 0:
                    continue

                processed_frame_count += 1
                print(
                    f"[VideoAnalysis] 프레임 처리 시작 - "
                    f"frame_no={current_frame_no}, processed_frame_count={processed_frame_count}"
                )

                active_persons = self.analyze_worker.run_inference_for_video(frame)
                people = list(active_persons.values())

                print(
                    f"[VideoAnalysis] 추론 완료 - frame_no={current_frame_no}, "
                    f"detected_people={len(people)}"
                )

                frame_entity = self.create_analysis_frame_usecase.execute(
                    session_id=session.id,
                    frame_no=current_frame_no,
                    frame_time_sec=current_frame_no / fps,
                    person_count=len(people),
                    frame_image_path=None,
                    processing_status=FrameProcessingStatus.PROCESSED,
                    error_message=None,
                )

                print(
                    f"[VideoAnalysis] 프레임 엔티티 저장 완료 - "
                    f"frame_id={frame_entity.id}, frame_no={current_frame_no}"
                )

                for person_index, person in enumerate(people, start=1):
                    print(
                        f"[VideoAnalysis] 사람 처리 시작 - "
                        f"frame_no={current_frame_no}, person_index={person_index}"
                    )

                    crop_image_path = self._save_crop_image(
                        session_id=session_id,
                        frame_no=current_frame_no,
                        person_index=person_index,
                        crop_image=person.crop_image,
                    )

                    print(
                        f"[VideoAnalysis] crop 저장 완료 - "
                        f"frame_no={current_frame_no}, person_index={person_index}, "
                        f"crop_image_path={crop_image_path}"
                    )

                    ocr_data = None
                    if person.crop_image is not None:
                        ocr_data = self.ocr_engine.extract_worker_id(person.crop_image)
                        print(
                            f"[VideoAnalysis] OCR 완료 - "
                            f"frame_no={current_frame_no}, person_index={person_index}, "
                            f"ocr_data={ocr_data}"
                        )

                    cmd = ProcessDetectionCommand(
                        session_id=session_id,
                        frame_id=frame_entity.id,
                        person_index=person_index,
                        helmet_status=ItemWearStatus.WEARING if person.has_helmet else ItemWearStatus.NOT_WEARING,
                        vest_status=ItemWearStatus.WEARING if person.has_vest else ItemWearStatus.NOT_WEARING,
                        employee_no=(ocr_data or {}).get("worker_id"),
                        ocr_text=(ocr_data or {}).get("raw_text"),
                        ocr_confidence=(ocr_data or {}).get("confidence"),
                        person_box_x=person.bbox[0],
                        person_box_y=person.bbox[1],
                        person_box_width=max(0, person.bbox[2] - person.bbox[0]),
                        person_box_height=max(0, person.bbox[3] - person.bbox[1]),
                        crop_image_path=crop_image_path,
                    )

                    self.process_detection_result_usecase.execute(cmd)
                    print(
                        f"[VideoAnalysis] detection_result 저장 완료 - "
                        f"frame_no={current_frame_no}, person_index={person_index}"
                    )

                print(f"[VideoAnalysis] 프레임 처리 완료 - frame_no={current_frame_no}")

            cap.release()
            print("[VideoAnalysis] VideoCapture release 완료")

            self.complete_analysis_session_usecase.execute(
                session_id=session_id,
                processed_frames=processed_frame_count,
            )
            print(f"[VideoAnalysis] 세션 완료 처리 성공 - session_id={session_id}")

            updated_session = self.get_analysis_session_usecase.execute(session_id)
            print(f"[VideoAnalysis] execute 종료 성공 - session_id={session_id}")

            return updated_session

        except Exception as e:
            cap.release()
            print(f"[VideoAnalysis] 예외 발생 - session_id={session_id}, error={str(e)}")

            self.fail_analysis_session_usecase.execute(session_id, str(e))
            print(f"[VideoAnalysis] 세션 실패 처리 완료 - session_id={session_id}")

            raise

    def _save_video_file(self, video_file, ext: str) -> str:
        saved_name = f"{uuid.uuid4().hex}{ext}"
        saved_path = os.path.join(self.upload_dir, saved_name)
        video_file.save(saved_path)
        print(f"[VideoAnalysis] _save_video_file 완료 - {saved_path}")
        return saved_path

    def _save_crop_image(self, session_id: str, frame_no: int, person_index: int, crop_image):
        if crop_image is None:
            print(
                f"[VideoAnalysis] crop 저장 스킵 - frame_no={frame_no}, "
                f"person_index={person_index}, reason=crop_image is None"
            )
            return None

        if getattr(crop_image, "size", 0) == 0:
            print(
                f"[VideoAnalysis] crop 저장 스킵 - frame_no={frame_no}, "
                f"person_index={person_index}, reason=empty image"
            )
            return None

        filename = f"{session_id}_f{frame_no}_p{person_index}.jpg"
        saved_path = os.path.join(self.crop_dir, filename)
        cv2.imwrite(saved_path, crop_image)
        print(
            f"[VideoAnalysis] _save_crop_image 완료 - "
            f"frame_no={frame_no}, person_index={person_index}, path={saved_path}"
        )
        return saved_path