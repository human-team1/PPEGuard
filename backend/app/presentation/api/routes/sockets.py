import os

import torch
from flask import request
from flask_socketio import emit

from app import socketio
from config.settings import Config
from app.application.dtos import AnalyzeFrameCommand
from app.application.services.analyze_worker_service import AnalyzeWorker
from app.application.services.video_analysis_ocr_service import VideoAnalysisOcrService
from app.application.usecases.analyze_frame_usecase import AnalyzeFrameUseCase
from app.infrastructure.dependencies import (
    build_detector,
    build_ocr_engine,
    build_realtime_event_service,
    build_segment_result_service,
)
from app.infrastructure.service_db.repositories.analysis_session_repository import (
    SQLAlchemyAnalysisSessionRepository,
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

detector = build_detector(MODEL_PATH, TRACKER_CONFIG)
worker = AnalyzeWorker(detector)
ocr_engine = build_ocr_engine()
ocr_service = VideoAnalysisOcrService(
    ocr_interval_sec=Config.OCR_INTERVAL_SEC,
    employee_no_regex=Config.EMPLOYEE_NO_REGEX,
    employee_no_min_length=Config.EMPLOYEE_NO_MIN_LENGTH,
    employee_no_max_length=Config.EMPLOYEE_NO_MAX_LENGTH,
)
session_repo = SQLAlchemyAnalysisSessionRepository()
realtime_event_service = build_realtime_event_service()
segment_result_service = build_segment_result_service(
    realtime_event_service=realtime_event_service,
)
analyze_frame_usecase = AnalyzeFrameUseCase(
    worker,
    session_repo=session_repo,
    ocr_service=ocr_service,
    ocr_engine=ocr_engine,
    segment_result_service=segment_result_service,
    realtime_event_service=realtime_event_service,
)
socket_session_map = {}


@socketio.on("connect")
def handle_connect():
    print("[Socket] client connected", flush=True)


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
        print(
            f"[Socket] webcam frame received - sid={request.sid}, session_id={command.session_id}",
            flush=True,
        )
        print("[SOCKET] payload decoded", flush=True)

        if command.session_id:
            socket_session_map[request.sid] = command.session_id

        print("[SOCKET] analysis started", flush=True)
        results = analyze_frame_usecase.execute(command)
        print("[SOCKET] analysis finished", flush=True)

        serialized_results = []
        for _, person in results.items():
            serialized_results.append(
                {
                    "id": person.id,
                    "bbox": person.bbox,
                    "has_vest": person.has_vest,
                    "has_helmet": person.has_helmet,
                    "is_safe": person.is_safe(),
                    "confidence": float(person.confidence),
                }
            )

        emit("results", {"persons": serialized_results})

    except Exception as e:
        print(f"[Socket] processing error: {e}", flush=True)
        emit("error", {"message": f"분석 중 오류 발생: {str(e)}"})


@socketio.on("disconnect")
def handle_disconnect():
    session_id = socket_session_map.pop(request.sid, None)
    if session_id:
        print(
            f"[Socket] disconnect flush triggered - sid={request.sid}, session_id={session_id}",
            flush=True,
        )
        analyze_frame_usecase.finalize_session(session_id, reason="disconnect")
    print("[Socket] client disconnected", flush=True)
