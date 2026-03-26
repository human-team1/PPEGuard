from datetime import datetime

from flask import Blueprint, request, jsonify, current_app

from config.settings import Config
from app.infrastructure.dependencies import build_video_analysis_service
from app.presentation.api.schemas.serializers import serialize
from app.application.services.video_analysis_service import VideoAnalysisService

video_bp = Blueprint("video", __name__, url_prefix="/api/v1/video")


@video_bp.route("", methods=["POST"])
def upload_video():
    try:
        video_file = request.files.get("file")
        requested_by = request.form.get("requested_by", "desktop-client")
        frame_interval_sec = float(
            request.form.get("frame_interval_sec", Config.FRAME_INTERVAL_SEC)
        )

        video_started_at = request.form.get("video_started_at")
        if video_started_at:
            video_started_at = datetime.fromisoformat(
                video_started_at.replace("Z", "+00:00")
            )
    except Exception as e:
        return jsonify({"error": "Bad Request", "details": str(e)}), 400

    try:
        service = build_video_analysis_service(
            model_path=current_app.config["YOLO_MODEL_PATH"],
            tracker_config=current_app.config["YOLO_TRACKER_CONFIG"],
        )
        session = service.execute(
            video_file=video_file,
            requested_by=requested_by,
            frame_interval_sec=frame_interval_sec,
            video_started_at=video_started_at,
        )
        return jsonify(serialize(session)), 201

    except ValueError as e:
        return jsonify({"error": "Bad Request", "details": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500


@video_bp.route("/stop", methods=["POST"])
# (추가) 목적/이유: 사용자 인터페이스(UI)로부터 동영상 분석 세션 중단(Stop) 
# 요청을 수신하여 해당 세션에 중단 신호를 전달하기 위한 API.
def stop_video():
    try:
        data = request.get_json() or {}
        session_id = data.get("session_id")
        
        # (추가) session_id가 없어도 현재 가장 최근 작동중인 동영상 세션을 중단하도록 허용
        VideoAnalysisService.stop_session(session_id)
        return jsonify({"message": "Stop request sent"}), 200
    except Exception as e:
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500
