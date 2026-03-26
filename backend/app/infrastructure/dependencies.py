import os

from config.settings import Config
from app.application.services.analyze_worker_service import AnalyzeWorker
from app.application.services.realtime_event_service import RealtimeEventService
from app.application.services.segment_persistence_service import SegmentPersistenceService
from app.application.services.segment_result_service import SegmentResultService
from app.application.services.video_analysis_file_service import VideoAnalysisFileService
from app.application.services.video_analysis_service import VideoAnalysisService
from app.application.services.webcam_result_persistence_service import WebcamResultPersistenceService
from app.application.services.webcam_realtime_pipeline_service import WebcamPipelineManager
from app.application.services.video_analysis_ocr_service import VideoAnalysisOcrService
from app.application.usecases.complete_analysis_session import CompleteAnalysisSessionUseCase
from app.application.usecases.fail_analysis_session import FailAnalysisSessionUseCase
from app.application.usecases.get_analysis_session import GetAnalysisSessionUseCase
from app.application.usecases.get_detection_result import GetDetectionResultUseCase
from app.application.usecases.get_recent_results import GetRecentResultsUseCase
from app.application.usecases.get_recent_sessions import GetRecentSessionsUseCase
from app.application.usecases.get_session_frames import GetSessionFramesUseCase
from app.application.usecases.get_session_results import GetSessionResultsUseCase
from app.application.usecases.get_session_segments import GetSessionSegmentsUseCase
from app.application.usecases.get_session_track_detail import GetSessionTrackDetailUseCase
from app.application.usecases.get_session_tracks import GetSessionTracksUseCase
from app.application.usecases.process_detection_result import ProcessDetectionResultUseCase
from app.application.usecases.start_analysis_session import StartAnalysisSessionUseCase
from app.application.usecases.stop_analysis_session import StopAnalysisSessionUseCase
from app.infrastructure.ai_analyzer.easyocr_engine import EasyOCREngine
from app.infrastructure.ai_analyzer.yolo_detector import YoloDetector
from app.infrastructure.customer_db.repositories.customer_detection_result_repository_impl import (
    SQLAlchemyCustomerDetectionResultRepository,
)
from app.infrastructure.service_db.repositories.analysis_frame_repository import (
    SQLAlchemyAnalysisFrameRepository,
)
from app.infrastructure.service_db.repositories.analysis_segment_person_result_repository import (
    SQLAlchemyAnalysisSegmentPersonResultRepository,
)
from app.infrastructure.service_db.repositories.analysis_segment_summary_repository import (
    SQLAlchemyAnalysisSegmentSummaryRepository,
)
from app.infrastructure.service_db.repositories.analysis_track_summary_repository import (
    SQLAlchemyAnalysisTrackSummaryRepository,
)
from app.infrastructure.service_db.repositories.analysis_session_repository import (
    SQLAlchemyAnalysisSessionRepository,
)
from app.infrastructure.service_db.repositories.detection_result_repository import (
    SQLAlchemyDetectionResultRepository,
)


def get_session_repo():
    return SQLAlchemyAnalysisSessionRepository()


def get_frame_repo():
    return SQLAlchemyAnalysisFrameRepository()


def get_result_repo():
    return SQLAlchemyDetectionResultRepository()


def get_segment_summary_repo():
    return SQLAlchemyAnalysisSegmentSummaryRepository()


def get_segment_person_result_repo():
    return SQLAlchemyAnalysisSegmentPersonResultRepository()


def get_customer_result_repo():
    return SQLAlchemyCustomerDetectionResultRepository()


def get_track_summary_repo():
    return SQLAlchemyAnalysisTrackSummaryRepository()


def build_start_session_usecase():
    return StartAnalysisSessionUseCase(get_session_repo())


def build_get_session_usecase():
    return GetAnalysisSessionUseCase(get_session_repo())


def build_get_recent_sessions_usecase():
    return GetRecentSessionsUseCase(get_session_repo())


def build_stop_session_usecase():
    return StopAnalysisSessionUseCase(get_session_repo())


def build_get_session_frames_usecase():
    return GetSessionFramesUseCase(get_session_repo(), get_frame_repo())


def build_get_session_results_usecase():
    return GetSessionResultsUseCase(
        get_session_repo(),
        get_result_repo(),
        get_frame_repo(),
    )


def build_get_session_segments_usecase():
    return GetSessionSegmentsUseCase(
        get_session_repo(),
        get_segment_summary_repo(),
        get_segment_person_result_repo(),
    )


def build_get_session_tracks_usecase():
    return GetSessionTracksUseCase(
        get_session_repo(),
        get_track_summary_repo(),
    )


def build_get_session_track_detail_usecase():
    return GetSessionTrackDetailUseCase(
        get_session_repo(),
        get_track_summary_repo(),
    )


def build_process_detection_result_usecase():
    return ProcessDetectionResultUseCase(
        session_repo=get_session_repo(),
        frame_repo=get_frame_repo(),
        result_repo=get_result_repo(),
        customer_result_repo=get_customer_result_repo(),
    )


def build_get_recent_results_usecase():
    return GetRecentResultsUseCase(get_result_repo())


def build_get_detection_result_usecase():
    return GetDetectionResultUseCase(get_result_repo())


def build_detector(model_path: str, tracker_config: str):
    return YoloDetector(model_path=model_path, tracker_config=tracker_config)


def build_ocr_engine():
    return EasyOCREngine()


def build_realtime_event_service():
    return RealtimeEventService()


def build_upload_paths():
    return (
        os.path.join(Config.UPLOAD_DIR, "videos"),
        os.path.join(Config.UPLOAD_DIR, "crops"),
    )


def build_segment_result_service(
    realtime_event_service=None,
    upload_dir: str | None = None,
    crop_dir: str | None = None,
    segment_seconds: float | None = None,
):
    upload_dir = upload_dir or build_upload_paths()[0]
    crop_dir = crop_dir or build_upload_paths()[1]
    realtime_service = realtime_event_service or build_realtime_event_service()
    return SegmentResultService(
        file_service=VideoAnalysisFileService(
            upload_dir=upload_dir,
            crop_dir=crop_dir,
        ),
        persistence_service=SegmentPersistenceService(
            segment_summary_repo=get_segment_summary_repo(),
            segment_person_result_repo=get_segment_person_result_repo(),
            realtime_event_service=realtime_service,
        ),
        segment_seconds=segment_seconds,
    )


def build_webcam_result_persistence_service(
    upload_dir: str | None = None,
    crop_dir: str | None = None,
):
    upload_dir = upload_dir or build_upload_paths()[0]
    crop_dir = crop_dir or build_upload_paths()[1]
    return WebcamResultPersistenceService(
        frame_repo=get_frame_repo(),
        detection_result_repo=get_result_repo(),
        track_summary_repo=get_track_summary_repo(),
        file_service=VideoAnalysisFileService(
            upload_dir=upload_dir,
            crop_dir=crop_dir,
        ),
    )


def build_webcam_pipeline_manager(
    model_path: str,
    tracker_config: str,
    realtime_event_service=None,
):
    realtime_service = realtime_event_service or build_realtime_event_service()
    ocr_service = VideoAnalysisOcrService(
        ocr_interval_sec=Config.OCR_INTERVAL_SEC,
        employee_no_regex=Config.EMPLOYEE_NO_REGEX,
        employee_number_min_confirm_count=Config.EMPLOYEE_NUMBER_MIN_CONFIRM_COUNT,
        employee_no_min_length=Config.EMPLOYEE_NO_MIN_LENGTH,
        employee_no_max_length=Config.EMPLOYEE_NO_MAX_LENGTH,
    )
    return WebcamPipelineManager(
        analyze_worker_factory=lambda: AnalyzeWorker(
            build_detector(model_path, tracker_config)
        ),
        ocr_engine=build_ocr_engine(),
        ocr_service=ocr_service,
        session_repo=get_session_repo(),
        result_persistence_service=build_webcam_result_persistence_service(),
        realtime_event_service=realtime_service,
        capture_fps=Config.WEBCAM_CAPTURE_FPS,
        analysis_fps=Config.WEBCAM_ANALYSIS_FPS,
        frame_queue_size=Config.WEBCAM_FRAME_QUEUE_SIZE,
        event_queue_size=Config.WEBCAM_EVENT_QUEUE_SIZE,
        result_window_seconds=Config.WEBCAM_RESULT_WINDOW_SECONDS,
        result_ttl_seconds=Config.SEGMENT_RESULT_TTL_SECONDS,
        track_expiry_seconds=Config.WEBCAM_TRACK_EXPIRY_SECONDS,
        max_track_ocr_count=Config.WEBCAM_MAX_TRACK_OCR_COUNT,
        yolo_worker_count=Config.YOLO_WORKER_COUNT,
        ocr_worker_count=Config.OCR_WORKER_COUNT,
        yolo_queue_size=Config.YOLO_QUEUE_SIZE,
        ocr_queue_size=Config.OCR_QUEUE_SIZE,
    )


def build_video_analysis_service(
    model_path: str,
    tracker_config: str,
    upload_dir: str | None = None,
    crop_dir: str | None = None,
):
    upload_dir = upload_dir or build_upload_paths()[0]
    crop_dir = crop_dir or build_upload_paths()[1]
    realtime_event_service = build_realtime_event_service()
    return VideoAnalysisService(
        upload_dir=upload_dir,
        crop_dir=crop_dir,
        analyze_worker=AnalyzeWorker(build_detector(model_path, tracker_config)),
        ocr_engine=build_ocr_engine(),
        segment_result_service=build_segment_result_service(
            realtime_event_service=realtime_event_service,
            upload_dir=upload_dir,
            crop_dir=crop_dir,
        ),
        realtime_event_service=realtime_event_service,
        start_analysis_session_usecase=StartAnalysisSessionUseCase(get_session_repo()),
        complete_analysis_session_usecase=CompleteAnalysisSessionUseCase(get_session_repo()),
        get_analysis_session_usecase=GetAnalysisSessionUseCase(get_session_repo()),
        fail_analysis_session_usecase=FailAnalysisSessionUseCase(get_session_repo()),
        session_repo=get_session_repo(),
    )
