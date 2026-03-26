import logging
import os

import torch
from flask import request

from app import socketio
from app.application.dtos import AnalyzeFrameCommand, StartSessionCommand
from app.application.usecases.analyze_frame_usecase import AnalyzeFrameUseCase
from app.domain.entities.analysis_session import AnalysisSourceType
from app.infrastructure.dependencies import (
    build_realtime_event_service,
    build_start_session_usecase,
    build_stop_session_usecase,
    build_webcam_pipeline_manager,
)
from app.presentation.api.schemas.serializers import serialize

torch.set_num_threads(1)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(
    BASE_DIR,
    "../../../infrastructure/ai_analyzer/models/yolo11s_ft_aug_best.pt",
)
TRACKER_CONFIG = os.path.join(
    BASE_DIR,
    "../../../infrastructure/ai_analyzer/configs/bytetrack.yaml",
)

realtime_event_service = build_realtime_event_service()
webcam_pipeline_manager = build_webcam_pipeline_manager(
    model_path=MODEL_PATH,
    tracker_config=TRACKER_CONFIG,
    realtime_event_service=realtime_event_service,
)
analyze_frame_usecase = AnalyzeFrameUseCase(
    webcam_pipeline_manager=webcam_pipeline_manager,
    realtime_event_service=realtime_event_service,
)
start_session_usecase = build_start_session_usecase()
stop_session_usecase = build_stop_session_usecase()
socket_session_map = {}
logger = logging.getLogger(__name__)


@socketio.on("connect")
def handle_connect():
    logger.info("[Socket] client connected sid=%s", request.sid)


@socketio.on("start_webcam_analysis")
def handle_start_webcam_analysis(data):
    payload = data or {}
    cmd = StartSessionCommand(
        source_type=AnalysisSourceType.WEBCAM,
        frame_interval_sec=int(payload.get("frame_interval_sec", 3)),
        source_name=payload.get("source_name") or "Webcam-Live",
        requested_by=payload.get("requested_by") or "socket-client",
    )
    session = start_session_usecase.execute(cmd)
    socket_session_map[request.sid] = session.session_id
    realtime_event_service.emit_session_status(
        session_id=session.session_id,
        source_type="WEBCAM",
        status="started",
    )
    logger.info("[Socket] webcam analysis started sid=%s session_id=%s", request.sid, session.session_id)
    return serialize(session)


@socketio.on("webcam_analysis_frame")
@socketio.on("frame")
def handle_webcam_analysis_frame(data):
    try:
        payload = data or {}
        image_data = payload.get("image")
        if not image_data:
            return

        expected_session_id = socket_session_map.get(request.sid)
        requested_session_id = payload.get("session_id")
        if not expected_session_id:
            logger.warning(
                "[Socket] webcam frame ignored inactive sid=%s session_id=%s frame_no=%s",
                request.sid,
                requested_session_id,
                payload.get("frame_no"),
            )
            return
        if requested_session_id != expected_session_id:
            logger.warning(
                "[Socket] webcam frame ignored session mismatch sid=%s expected_session_id=%s session_id=%s frame_no=%s",
                request.sid,
                expected_session_id,
                requested_session_id,
                payload.get("frame_no"),
            )
            return

        command = AnalyzeFrameCommand(
            image_base64=image_data,
            session_id=requested_session_id,
            frame_no=payload.get("frame_no"),
        )

        if command.session_id:
            socket_session_map[request.sid] = command.session_id

        analyze_frame_usecase.execute(command)

    except Exception as exc:
        logger.exception(
            "[Socket] frame processing failed sid=%s session_id=%s",
            request.sid,
            data.get("session_id") if isinstance(data, dict) else None,
        )
        realtime_event_service.emit_error(f"분석 중 오류 발생: {str(exc)}")


@socketio.on("stop_webcam_analysis")
def handle_stop_webcam_analysis(data):
    payload = data or {}
    session_id = payload.get("session_id") or socket_session_map.get(request.sid)
    if not session_id:
        return {"error": "Session not found"}

    analyze_frame_usecase.finalize_session(session_id, reason="stop")
    session = stop_session_usecase.execute(session_id)
    realtime_event_service.emit_session_status(
        session_id=session_id,
        source_type="WEBCAM",
        status="stopped",
    )
    socket_session_map.pop(request.sid, None)
    logger.info("[Socket] webcam analysis stopped sid=%s session_id=%s", request.sid, session_id)
    return serialize(session)


@socketio.on("disconnect")
def handle_disconnect():
    session_id = socket_session_map.pop(request.sid, None)
    if session_id:
        logger.info(
            "[Socket] disconnect finalize sid=%s session_id=%s",
            request.sid,
            session_id,
        )
        analyze_frame_usecase.finalize_session(session_id, reason="disconnect")
    logger.info("[Socket] client disconnected sid=%s", request.sid)
