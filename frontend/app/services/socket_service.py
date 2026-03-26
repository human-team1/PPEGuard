import base64
import logging

import cv2
import numpy as np
import socketio
from PySide6.QtCore import QObject, Signal


logger = logging.getLogger(__name__)


class SocketService(QObject):
    analysis_progress_ready = Signal(dict)
    analysis_frame_result_ready = Signal(dict)
    analysis_segment_saved = Signal(dict)
    analysis_session_status_changed = Signal(dict)
    connected = Signal()
    disconnected = Signal()
    error_occurred = Signal(str)

    def __init__(self, server_url: str = "http://127.0.0.1:5000"):
        super().__init__()
        self.server_url = server_url
        self.sio = socketio.Client(logger=False, engineio_logger=False)
        self.session_id = None
        self.streaming_enabled = False
        self._setup_handlers()

    def _setup_handlers(self):
        @self.sio.on("connect")
        def on_connect():
            logger.info("[Socket] connected url=%s", self.server_url)
            self.connected.emit()

        @self.sio.on("disconnect")
        def on_disconnect():
            logger.info("[Socket] disconnected")
            self.disconnected.emit()

        @self.sio.on("analysis_progress")
        def on_analysis_progress(data):
            logger.debug("[Socket] analysis_progress received session_id=%s", data.get("session_id"))
            self.analysis_progress_ready.emit(data)

        @self.sio.on("analysis_frame_result")
        def on_analysis_frame_result(data):
            logger.debug(
                "[Socket] analysis_frame_result received session_id=%s detections=%s",
                data.get("session_id"),
                len(data.get("detections", [])),
            )
            self.analysis_frame_result_ready.emit(data)

        @self.sio.on("analysis_track_confirmed")
        def on_analysis_track_confirmed(data):
            logger.info(
                "[OCR] confirmed track_id=%s employee_no=%s",
                data.get("track_id"),
                data.get("employee_id"),
            )

        @self.sio.on("analysis_segment_saved")
        def on_analysis_segment_saved(data):
            logger.info(
                "[Segment] saved session_id=%s segment_index=%s people=%s",
                data.get("session_id"),
                data.get("segment_index"),
                len(data.get("person_results", [])),
            )
            self.analysis_segment_saved.emit(data)

        @self.sio.on("analysis_session_status")
        def on_analysis_session_status(data):
            self.analysis_session_status_changed.emit(data)

        @self.sio.on("error")
        def on_error(data):
            message = data.get("message", "알 수 없는 오류")
            logger.error("[Socket] server error message=%s", message)
            self.error_occurred.emit(message)

    def ensure_connected(self):
        return self.connect_server()

    def connect_server(self):
        try:
            if self.sio.connected:
                return True

            logger.info("[Socket] connecting url=%s", self.server_url)
            self.sio.connect(self.server_url, transports=["websocket", "polling"])
            return self.sio.connected
        except Exception as e:
            logger.exception("[Socket] connect failed url=%s", self.server_url)
            self.error_occurred.emit(f"서버 연결 실패: {str(e)}")
            return False

    def disconnect_server(self):
        self.streaming_enabled = False
        self.session_id = None
        if self.sio.connected:
            logger.info("[Socket] disconnect requested")
            self.sio.disconnect()

    def start_streaming(self, session_id: str):
        self.session_id = session_id
        self.streaming_enabled = True
        connected = self.connect_server()
        logger.info(
            "[AnalysisSession] started session_id=%s source=webcam connected=%s",
            session_id,
            connected,
        )

    def stop_streaming(self):
        if self.streaming_enabled or self.session_id:
            logger.info("[AnalysisSession] stopped session_id=%s source=webcam", self.session_id)
        self.streaming_enabled = False
        self.session_id = None

    def send_frame(self, frame_np: np.ndarray):
        if not self.streaming_enabled:
            return

        if not self.session_id:
            logger.warning("[Webcam] frame send skipped missing_session_id")
            return

        if not self.sio.connected:
            connected = self.connect_server()
            if not connected:
                return

        try:
            h, w = frame_np.shape[:2]
            target_width = 640
            if w > target_width:
                aspect_ratio = h / w
                frame_np = cv2.resize(frame_np, (target_width, int(target_width * aspect_ratio)))

            _, buffer = cv2.imencode(".jpg", frame_np, [cv2.IMWRITE_JPEG_QUALITY, 60])
            b64_frame = base64.b64encode(buffer).decode("utf-8")

            self.sio.emit(
                "frame",
                {
                    "image": f"data:image/jpeg;base64,{b64_frame}",
                    "session_id": self.session_id,
                },
            )
        except Exception as e:
            logger.exception("[Webcam] frame send failed session_id=%s", self.session_id)
            self.error_occurred.emit(f"프레임 전송 실패: {str(e)}")
