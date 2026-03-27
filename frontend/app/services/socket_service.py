import base64
import logging
import os

import cv2
import numpy as np
import socketio
from PySide6.QtCore import QObject, Signal


logger = logging.getLogger(__name__)


class SocketService(QObject):
    analysis_progress_ready = Signal(dict)
    analysis_frame_result_ready = Signal(dict)
    analysis_track_confirmed_ready = Signal(dict)
    analysis_segment_saved = Signal(dict)
    analysis_session_status_changed = Signal(dict)
    connected = Signal()
    disconnected = Signal()
    connection_state_changed = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, server_url: str = "http://127.0.0.1:5000"):
        super().__init__()
        self.server_url = server_url
        self.sio = socketio.Client(
            logger=False,
            engineio_logger=False,
            reconnection=True,
        )
        self.session_id = None
        self.analysis_active = False
        self.next_frame_no = 0
        self._was_previously_connected = False
        # diagnostic: None keeps the default transport negotiation order.
        # temporary debugging: switch to ["polling"] or ["websocket"] when comparing behaviors.
        transport_env = (os.getenv("PPEGUARD_SOCKET_TRANSPORT") or "").strip().lower()
        self._connect_transports = [transport_env] if transport_env in {"polling", "websocket"} else None
        self._setup_handlers()

    def _setup_handlers(self):
        @self.sio.on("connect")
        def on_connect():
            is_reconnect = self._was_previously_connected
            logger.info(
                "[Socket] connected url=%s sid=%s transports=%s",
                self.server_url,
                self.sio.sid,
                self._connect_transports or "default",
            )
            self._was_previously_connected = True
            self.connected.emit()
            self.connection_state_changed.emit("reconnected" if is_reconnect else "connected")

        @self.sio.on("disconnect")
        def on_disconnect():
            logger.warning(
                "[Socket] disconnected url=%s sid=%s transports=%s",
                self.server_url,
                self.sio.sid,
                self._connect_transports or "default",
            )
            self.disconnected.emit()
            self.connection_state_changed.emit("disconnected")

        @self.sio.on("connect_error")
        def on_connect_error(data):
            logger.error(
                "[Socket] connect_error url=%s transports=%s data=%s",
                self.server_url,
                self._connect_transports or "default",
                data,
            )

        @self.sio.on("analysis_progress")
        def on_analysis_progress(data):
            logger.debug("[Socket] analysis_progress received session_id=%s", data.get("session_id"))
            self.analysis_progress_ready.emit(data)

        @self.sio.on("analysis_frame_result")
        def on_analysis_frame_result(data):
            logger.info(
                "[Socket] analysis_frame_result received session_id=%s frame_no=%s payload_keys=%s tracks_count=%s detections_count=%s image_len=%s",
                data.get("session_id"),
                data.get("frame_no"),
                sorted(list(data.keys())),
                data.get("tracks_count", 0),
                len(data.get("detections", [])),
                0,
            )
            self.analysis_frame_result_ready.emit(data)

        @self.sio.on("analysis_track_confirmed")
        def on_analysis_track_confirmed(data):
            logger.info(
                "[OCR] confirmed track_id=%s employee_no=%s",
                data.get("track_id"),
                data.get("employee_id"),
            )
            self.analysis_track_confirmed_ready.emit(data)

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
            message = data.get("message", "Unknown error")
            logger.error("[Socket] server error message=%s", message)
            self.error_occurred.emit(message)

    def ensure_connected(self):
        return self.connect_server()

    def configure_transports(self, transports: list[str] | None = None):
        self._connect_transports = list(transports) if transports else None

    def has_active_session(self) -> bool:
        return bool(self.analysis_active and self.session_id)

    def connect_server(self):
        try:
            if self.sio.connected:
                return True

            logger.info(
                "[Socket] connecting url=%s transports=%s",
                self.server_url,
                self._connect_transports or "default",
            )
            connect_kwargs = {}
            if self._connect_transports is not None:
                connect_kwargs["transports"] = self._connect_transports

            self.sio.connect(self.server_url, **connect_kwargs)
            logger.info(
                "[Socket] connect finished connected=%s sid=%s",
                self.sio.connected,
                self.sio.sid,
            )
            return self.sio.connected
        except Exception as e:
            logger.exception(
                "[Socket] connect failed url=%s transports=%s",
                self.server_url,
                self._connect_transports or "default",
            )
            self.error_occurred.emit(f"서버 연결 실패: {str(e)}")
            return False

    def disconnect_server(self):
        self.analysis_active = False
        self.session_id = None
        self.next_frame_no = 0
        self._was_previously_connected = False
        if self.sio.connected:
            logger.info(
                "[Socket] disconnect requested url=%s sid=%s",
                self.server_url,
                self.sio.sid,
            )
            self.sio.disconnect()

    def start_webcam_analysis(
        self,
        source_name: str = "Webcam-Live",
        frame_interval: int = 3,
    ) -> dict:
        connected = self.connect_server()
        if not connected:
            raise ConnectionError("소켓 서버 연결에 실패했습니다.")

        payload = self.sio.call(
            "start_webcam_analysis",
            {
                "source_name": source_name,
                "frame_interval_sec": frame_interval,
                "requested_by": "desktop-client",
            },
            timeout=5,
        )
        self.session_id = payload.get("session_id")
        self.analysis_active = bool(self.session_id)
        self.next_frame_no = 0
        logger.info(
            "[AnalysisSession] started session_id=%s source=webcam connected=%s",
            self.session_id,
            connected,
        )
        return payload

    def stop_webcam_analysis(self, session_id: str | None = None) -> dict:
        target_session_id = session_id or self.session_id
        if not target_session_id:
            raise ConnectionError("중지할 웹캠 세션이 없습니다.")
        connected = self.connect_server()
        if not connected:
            raise ConnectionError("소켓 서버 연결에 실패했습니다.")

        payload = self.sio.call(
            "stop_webcam_analysis",
            {"session_id": target_session_id},
            timeout=5,
        )
        logger.info("[AnalysisSession] stopped session_id=%s source=webcam", target_session_id)
        self.analysis_active = False
        self.session_id = None
        self.next_frame_no = 0
        return payload

    def send_analysis_sample(self, frame_np: np.ndarray):
        if not self.analysis_active:
            logger.debug("[Webcam] analysis sample skipped inactive session_id=%s", self.session_id)
            return

        if not self.session_id:
            logger.warning("[Webcam] sample send skipped missing_session_id")
            return

        if not self.sio.connected:
            connected = self.connect_server()
            if not connected:
                return

        try:
            self.next_frame_no += 1
            frame_no = self.next_frame_no
            h, w = frame_np.shape[:2]
            target_width = 640
            if w > target_width:
                aspect_ratio = h / w
                frame_np = cv2.resize(frame_np, (target_width, int(target_width * aspect_ratio)))
                h, w = frame_np.shape[:2]

            _, buffer = cv2.imencode(".jpg", frame_np, [cv2.IMWRITE_JPEG_QUALITY, 60])
            b64_frame = base64.b64encode(buffer).decode("utf-8")

            self.sio.emit(
                "webcam_analysis_frame",
                {
                    "image": f"data:image/jpeg;base64,{b64_frame}",
                    "session_id": self.session_id,
                    "frame_no": frame_no,
                    "frame_width": w,
                    "frame_height": h,
                },
            )
            logger.debug(
                "[Webcam] analysis sample sent session_id=%s frame_no=%s image_len=%s",
                self.session_id,
                frame_no,
                len(b64_frame),
            )
        except Exception as e:
            logger.exception("[Webcam] sample send failed session_id=%s", self.session_id)
            self.error_occurred.emit(f"프레임 전송 실패: {str(e)}")
