import logging
import os
import time
from datetime import datetime

import cv2

from config.settings import Config
from app.application.dtos import StartSessionCommand
from app.application.services.segment_window_service import SegmentWindowService
from app.application.services.video_analysis_file_service import VideoAnalysisFileService
from app.application.services.video_analysis_ocr_service import VideoAnalysisOcrService
from app.application.services.video_segment_pipeline_service import (
    VideoSegmentPipelineService,
)
from app.domain.entities.analysis_session import AnalysisSourceType


logger = logging.getLogger(__name__)


class VideoAnalysisService:
    ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}
    
    # (추가) 목적/이유: 동영상 분석 도중 사용자 요청에 의한 중단(Stop) 기능 지원을 위해 
    # 클래스 레벨에서 중단된 세션 ID를 추적하기 위한 플래그 세트 도입.
    _stopped_sessions = set()
    # (추가) 목적/이유: 동기 블로킹 방식으로 인해 frontend가 세션 ID를 모르는 상태에서도 
    # 현재 분석 중인 단일 세션을 중단할 수 있도록 최신 세션 ID를 추적함.
    _current_processing_session = None

    @classmethod
    def stop_session(cls, session_id: str | None = None):
        target_session = session_id or cls._current_processing_session
        if target_session:
            print(f"[VideoAnalysis] stop_session requested for {target_session}")
            cls._stopped_sessions.add(target_session)

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
        session_repo,
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
        self.session_repo = session_repo

        self.ocr_interval_sec = Config.OCR_INTERVAL_SEC
        self.employee_no_regex = Config.EMPLOYEE_NO_REGEX
        self.employee_number_min_confirm_count = Config.EMPLOYEE_NUMBER_MIN_CONFIRM_COUNT
        self.employee_no_min_length = Config.EMPLOYEE_NO_MIN_LENGTH
        self.employee_no_max_length = Config.EMPLOYEE_NO_MAX_LENGTH
        self.segment_duration_seconds = Config.SEGMENT_DURATION_SECONDS
        self.analysis_fps = Config.ANALYSIS_FPS
        self.max_concurrent_segments = Config.MAX_CONCURRENT_SEGMENTS
        self.yolo_worker_count = Config.YOLO_WORKER_COUNT
        self.ocr_worker_count = Config.OCR_WORKER_COUNT

        self.file_service = VideoAnalysisFileService(
            upload_dir=self.upload_dir,
            crop_dir=self.crop_dir,
        )
        self.ocr_service = VideoAnalysisOcrService(
            ocr_interval_sec=self.ocr_interval_sec,
            employee_no_regex=self.employee_no_regex,
            employee_number_min_confirm_count=self.employee_number_min_confirm_count,
            employee_no_min_length=self.employee_no_min_length,
            employee_no_max_length=self.employee_no_max_length,
        )
        self.segment_window_service = SegmentWindowService(
            segment_seconds=self.segment_duration_seconds,
        )

    def execute(
        self,
        video_file,
        frame_interval_sec: int,
        requested_by: str = "desktop-client",
        video_started_at: str | None = None,
    ):
        started_at = time.perf_counter()
        logger.info("[AnalysisSession] video analysis requested requested_by=%s", requested_by)

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
        cap.release()

        logger.info(
            "[VideoAnalysis] config fps=%.2f analysis_fps=%s segment_seconds=%s max_segments=%s yolo_workers=%s ocr_workers=%s",
            fps,
            self.analysis_fps,
            self.segment_duration_seconds,
            self.max_concurrent_segments,
            self.yolo_worker_count,
            self.ocr_worker_count,
        )
        logger.info(
            "[VideoAnalysis] frame_interval_sec is metadata only analysis_fps=%s",
            self.analysis_fps,
        )

        start_cmd = StartSessionCommand(
            source_type=AnalysisSourceType.VIDEO_FILE,
            total_frames=total_frames,
            frame_interval_sec=max(int(round(frame_interval_sec or 0)), 1),
            source_name=original_filename,
            requested_by=requested_by,
            video_started_at=video_started_at_dt,
        )
        session = self.start_analysis_session_usecase.execute(start_cmd)
        session_id = session.session_id
        
        # (추가) 현재 처리 중인 세션 ID 등록하여 세션 ID를 모르는 프론트엔드에서도 중단 가능케 함
        VideoAnalysisService._current_processing_session = session_id

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
            pipeline = VideoSegmentPipelineService(
                analyze_worker=self.analyze_worker,
                ocr_engine=self.ocr_engine,
                ocr_service=self.ocr_service,
                file_service=self.segment_result_service.file_service,
                persistence_service=self.segment_result_service.persistence_service,
                realtime_event_service=self.realtime_event_service,
                segment_window_service=self.segment_window_service,
                analysis_fps=self.analysis_fps,
                max_concurrent_segments=self.max_concurrent_segments,
                yolo_worker_count=self.yolo_worker_count,
                ocr_worker_count=self.ocr_worker_count,
            )
            try:
                processed_frame_count = pipeline.process_video(
                    session=session,
                    video_path=saved_video_path,
                    fps=fps,
                    total_frames=total_frames,
                    total_time_sec=total_time_sec,
                    source_type=AnalysisSourceType.VIDEO_FILE.value,
                    stop_signal=lambda: session_id in VideoAnalysisService._stopped_sessions,
                )
            finally:
                pipeline.close()

            # (추가) 목적/이유: 사용자 요청에 의한 중단 시 실제 프레임/세그먼트/추론 데이터를 DB에서 지움.
            if processed_frame_count is None:
                VideoAnalysisService._stopped_sessions.discard(session_id)
                self.fail_analysis_session_usecase.execute(session_id, "Analysis stopped by user")
                self.session_repo.delete_session_data(session_id)
                self.realtime_event_service.emit_session_status(
                    session_id=session_id,
                    source_type=AnalysisSourceType.VIDEO_FILE.value,
                    status="stopped",
                )
                VideoAnalysisService._current_processing_session = None
                return self.get_analysis_session_usecase.execute(session_id)

            self.complete_analysis_session_usecase.execute(
                session_id=session_id,
                processed_frames=processed_frame_count,
            )
            logger.info(
                "[AnalysisSession] completed session_id=%s processed_frames=%s elapsed_sec=%.2f",
                session_id,
                processed_frame_count,
                time.perf_counter() - started_at,
            )
            self.realtime_event_service.emit_session_status(
                session_id=session_id,
                source_type=AnalysisSourceType.VIDEO_FILE.value,
                status="completed",
            )

            updated_session = self.get_analysis_session_usecase.execute(session_id)
            VideoAnalysisService._current_processing_session = None
            return updated_session

        except Exception as exc:
            logger.exception("[AnalysisSession] failed session_id=%s", session_id)
            self.fail_analysis_session_usecase.execute(session_id, str(exc))
            self.realtime_event_service.emit_session_status(
                session_id=session_id,
                source_type=AnalysisSourceType.VIDEO_FILE.value,
                status="failed",
            )
            VideoAnalysisService._current_processing_session = None
            raise
