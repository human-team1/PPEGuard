import logging
import os

import torch
from flask import request

from app import socketio
from app.application.dtos import AnalyzeFrameCommand
from app.application.usecases.analyze_frame_usecase import AnalyzeFrameUseCase
from app.infrastructure.dependencies import (
    build_realtime_event_service,
    build_webcam_pipeline_manager,
)

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
socket_session_map = {}
logger = logging.getLogger(__name__)


@socketio.on("connect")
def handle_connect():
    logger.info("[Socket] client connected sid=%s", request.sid)


@socketio.on("frame")
def handle_frame(data):
    try:
        image_data = data.get("image")
        if not image_data:
            return

        command = AnalyzeFrameCommand(
            image_base64=image_data,
            session_id=data.get("session_id"),
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
