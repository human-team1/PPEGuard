import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from config.settings import Config
from app.application.dtos import ProcessDetectionCommand, StartSessionCommand
from app.domain.entities.analysis_session import AnalysisSourceType
from app.domain.entities.detection_result import ItemWearStatus
from app.infrastructure.dependencies import (
    build_get_recent_sessions_usecase,
    build_get_session_frames_usecase,
    build_get_session_results_usecase,
    build_get_session_segments_usecase,
    build_get_session_track_detail_usecase,
    build_get_session_tracks_usecase,
    build_get_session_usecase,
    build_process_detection_result_usecase,
    build_start_session_usecase,
    build_stop_session_usecase,
)
from app.presentation.api.schemas.serializers import serialize


sessions_bp = Blueprint("sessions", __name__, url_prefix="/api/v1/sessions")
logger = logging.getLogger(__name__)


@sessions_bp.route("", methods=["POST"])
def create_session():
    """
    `frame_interval_sec` remains session metadata for compatibility.
    Video sampling is determined by backend `ANALYSIS_FPS`.
    """
    data = request.get_json() or {}
    try:
        source_type_str = data.get("source_type", "WEBCAM")
        source_type = AnalysisSourceType[source_type_str]

        video_started_at = data.get("video_started_at")
        if video_started_at:
            video_started_at = datetime.fromisoformat(
                video_started_at.replace("Z", "+00:00")
            )

        cmd = StartSessionCommand(
            source_type=source_type,
            frame_interval_sec=int(data.get("frame_interval_sec", Config.FRAME_INTERVAL_SEC)),
            source_name=data.get("source_name"),
            requested_by=data.get("requested_by"),
            total_frames=data.get("total_frames"),
            video_started_at=video_started_at,
        )
    except Exception as e:
        return jsonify({"error": "Bad Request", "details": str(e)}), 400

    usecase = build_start_session_usecase()
    session = usecase.execute(cmd)

    return jsonify(serialize(session)), 201


@sessions_bp.route("", methods=["GET"])
def list_sessions():
    try:
        limit = int(request.args.get("limit", 20))
    except ValueError:
        return jsonify({"error": "Invalid limit parameter"}), 400

    usecase = build_get_recent_sessions_usecase()
    sessions = usecase.execute(limit=limit)
    return jsonify(serialize(sessions)), 200


@sessions_bp.route("/<session_id>", methods=["GET"])
def get_session(session_id: str):
    usecase = build_get_session_usecase()
    session = usecase.execute(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(serialize(session)), 200


@sessions_bp.route("/<session_id>/frames", methods=["GET"])
def get_session_frames(session_id: str):
    usecase = build_get_session_frames_usecase()
    try:
        frames = usecase.execute(session_id)
        return jsonify(serialize(frames)), 200
    except ValueError:
        return jsonify({"error": "Session not found"}), 404


@sessions_bp.route("/<session_id>/stop", methods=["POST"])
def stop_session(session_id: str):
    try:
        from app.presentation.api.routes.sockets import analyze_frame_usecase

        logger.info("[AnalysisSession] stop requested session_id=%s", session_id)
        analyze_frame_usecase.finalize_session(session_id, reason="stop")
    except Exception:
        pass

    usecase = build_stop_session_usecase()
    try:
        session = usecase.execute(session_id)
        return jsonify(serialize(session)), 200
    except ValueError:
        return jsonify({"error": "Session not found"}), 404


@sessions_bp.route("/<session_id>/results", methods=["GET"])
def get_session_results(session_id: str):
    usecase = build_get_session_results_usecase()
    try:
        results = usecase.execute(session_id)
        return jsonify(serialize(results)), 200
    except ValueError:
        return jsonify({"error": "Session not found"}), 404


@sessions_bp.route("/<session_id>/segments", methods=["GET"])
def get_session_segments(session_id: str):
    usecase = build_get_session_segments_usecase()
    try:
        segments = usecase.execute(session_id)
        return jsonify(serialize(segments)), 200
    except ValueError:
        return jsonify({"error": "Session not found"}), 404


@sessions_bp.route("/<session_id>/tracks", methods=["GET"])
def get_session_tracks(session_id: str):
    usecase = build_get_session_tracks_usecase()
    try:
        tracks = usecase.execute(session_id)
        return jsonify(serialize(tracks)), 200
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            return jsonify({"error": message}), 404
        return jsonify({"error": message}), 400


@sessions_bp.route("/<session_id>/tracks/<int:track_id>", methods=["GET"])
def get_session_track_detail(session_id: str, track_id: int):
    usecase = build_get_session_track_detail_usecase()
    try:
        track = usecase.execute(session_id, track_id)
        return jsonify(serialize(track)), 200
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            return jsonify({"error": message}), 404
        return jsonify({"error": message}), 400


@sessions_bp.route("/<session_id>/results", methods=["POST"])
def process_result(session_id: str):
    data = request.get_json() or {}
    try:
        cmd = ProcessDetectionCommand(
            session_id=session_id,
            frame_id=data["frame_id"],
            person_index=data["person_index"],
            helmet_status=ItemWearStatus(data["helmet_status"]),
            vest_status=ItemWearStatus(data["vest_status"]),
            employee_no=data.get("employee_no"),
            ocr_text=data.get("ocr_text"),
            ocr_confidence=data.get("ocr_confidence"),
            person_box_x=data.get("person_box_x"),
            person_box_y=data.get("person_box_y"),
            person_box_width=data.get("person_box_width"),
            person_box_height=data.get("person_box_height"),
            crop_image_path=data.get("crop_image_path"),
        )
    except Exception as e:
        return jsonify({"error": "Bad Request", "details": str(e)}), 400

    usecase = build_process_detection_result_usecase()

    try:
        result = usecase.execute(cmd)
        return jsonify(serialize(result)), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500
