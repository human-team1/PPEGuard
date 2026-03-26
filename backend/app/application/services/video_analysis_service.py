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
                )
            finally:
                pipeline.close()

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
            return updated_session

        except Exception as exc:
            logger.exception("[AnalysisSession] failed session_id=%s", session_id)
            self.fail_analysis_session_usecase.execute(session_id, str(exc))
            self.realtime_event_service.emit_session_status(
                session_id=session_id,
                source_type=AnalysisSourceType.VIDEO_FILE.value,
                status="failed",
            )
            raise
