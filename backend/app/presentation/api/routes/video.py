from datetime import datetime
from flask import Blueprint, request, jsonify, current_app

from app.infrastructure.service_db.repositories.analysis_session_repository import SQLAlchemyAnalysisSessionRepository
from app.infrastructure.service_db.repositories.analysis_frame_repository import SQLAlchemyAnalysisFrameRepository
from app.infrastructure.service_db.repositories.detection_result_repository import SQLAlchemyDetectionResultRepository
from app.infrastructure.customer_db.repositories.customer_detection_result_repository_impl import SQLAlchemyCustomerDetectionResultRepository

from app.infrastructure.ai_analyzer.yolo_detector import YoloDetector
from app.infrastructure.ai_analyzer.easyocr_engine import EasyOCREngine

from app.application.services.analyze_worker_service import AnalyzeWorker
from app.application.usecases.start_analysis_session import StartAnalysisSessionUseCase
from app.application.usecases.get_analysis_session import GetAnalysisSessionUseCase
from app.application.usecases.complete_analysis_session import CompleteAnalysisSessionUseCase
from app.application.usecases.fail_analysis_session import FailAnalysisSessionUseCase
from app.application.usecases.create_analysis_frame import CreateAnalysisFrameUseCase
from app.application.usecases.process_detection_result import ProcessDetectionResultUseCase
from app.application.services.video_analysis_service import VideoAnalysisService
from app.presentation.api.schemas.serializers import serialize

video_bp = Blueprint("video", __name__, url_prefix="/api/v1/video")

def get_session_repo():
    return SQLAlchemyAnalysisSessionRepository()


def get_frame_repo():
    return SQLAlchemyAnalysisFrameRepository()


def get_result_repo():
    return SQLAlchemyDetectionResultRepository()


def get_customer_result_repo():
    host = current_app.config.get("CUSTOMER_DB_HOST")
    db_name = current_app.config.get("CUSTOMER_DB_NAME")
    user = current_app.config.get("CUSTOMER_DB_USER")

    if not host or not db_name or not user:
        return None

    return SQLAlchemyCustomerDetectionResultRepository()


def get_detector():
    return YoloDetector(
        model_path=current_app.config["YOLO_MODEL_PATH"],
        tracker_config=current_app.config["YOLO_TRACKER_CONFIG"],
    )

def get_ocr_engine():
    return EasyOCREngine()


def build_video_service():
    return VideoAnalysisService(
        upload_dir="./uploads/videos",
        crop_dir="./uploads/crops",
        analyze_worker=AnalyzeWorker(get_detector()),
        ocr_engine=get_ocr_engine(),
        start_analysis_session_usecase=StartAnalysisSessionUseCase(get_session_repo()),
        create_analysis_frame_usecase=CreateAnalysisFrameUseCase(get_frame_repo()),
        process_detection_result_usecase=ProcessDetectionResultUseCase(
            session_repo=get_session_repo(),
            frame_repo=get_frame_repo(),
            result_repo=get_result_repo(),
            customer_result_repo=get_customer_result_repo(),
        ),
        complete_analysis_session_usecase=CompleteAnalysisSessionUseCase(get_session_repo()),
        get_analysis_session_usecase=GetAnalysisSessionUseCase(get_session_repo()),
        fail_analysis_session_usecase=FailAnalysisSessionUseCase(get_session_repo()),
    )


@video_bp.route("", methods=["POST"])
def upload_video():
    try:
        video_file = request.files.get("file")
        requested_by = request.form.get("requested_by", "desktop-client")
        frame_interval_sec = int(request.form.get("frame_interval_sec", 3))

        video_started_at = request.form.get("video_started_at")
        if video_started_at:
            video_started_at = datetime.fromisoformat(
                video_started_at.replace("Z", "+00:00")
            )
    except Exception as e:
        return jsonify({"error": "Bad Request", "details": str(e)}), 400

    try:
        service = build_video_service()
        session = service.execute(
            video_file=video_file,
            requested_by=requested_by,
            frame_interval_sec=frame_interval_sec,
            video_started_at=video_started_at
        )
        return jsonify(serialize(session)), 201

    except ValueError as e:
        return jsonify({"error": "Bad Request", "details": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500