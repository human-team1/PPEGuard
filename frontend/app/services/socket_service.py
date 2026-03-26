import base64
import time

import cv2
import numpy as np
import socketio
from PySide6.QtCore import QObject, Signal


class SocketService(QObject):
    results_ready = Signal(dict)
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
        self.is_busy = False
        self.session_id = None
        self.streaming_enabled = False
        self._last_log_at = 0.0
        self._setup_handlers()

    def _setup_handlers(self):
        @self.sio.on("connect")
        def on_connect():
            print(f"[FRONT] socket connected - url={self.server_url}", flush=True)
            self.connected.emit()

        @self.sio.on("disconnect")
        def on_disconnect():
            print("[FRONT] socket disconnected", flush=True)
            self.is_busy = False
            self.disconnected.emit()

        @self.sio.on("results")
        def on_results(data):
            self.is_busy = False
            self.results_ready.emit(data)

        @self.sio.on("analysis_progress")
        def on_analysis_progress(data):
            self.analysis_progress_ready.emit(data)

        @self.sio.on("analysis_frame_result")
        def on_analysis_frame_result(data):
            self.analysis_frame_result_ready.emit(data)

        @self.sio.on("analysis_segment_saved")
        def on_analysis_segment_saved(data):
            print(
                "[FRONT] analysis_segment_saved received - "
                f"session_id={data.get('session_id')}, "
                f"segment_index={data.get('segment_index')}, "
                f"people={len(data.get('person_results', []))}",
                flush=True,
            )
            self.analysis_segment_saved.emit(data)

        @self.sio.on("analysis_session_status")
        def on_analysis_session_status(data):
            self.analysis_session_status_changed.emit(data)

        @self.sio.on("error")
        def on_error(data):
            self.is_busy = False
            message = data.get("message", "알 수 없는 오류")
            print(f"[FRONT][ERROR] socket server error: {message}", flush=True)
            self.error_occurred.emit(message)

    def ensure_connected(self):
        return self.connect_server()

    def connect_server(self):
        try:
            if self.sio.connected:
                return True

            print(f"[FRONT] socket connecting - url={self.server_url}", flush=True)
            self.sio.connect(self.server_url, transports=["websocket", "polling"])
            return self.sio.connected
        except Exception as e:
            print(f"[FRONT][ERROR] socket connect failed: {e}", flush=True)
            self.error_occurred.emit(f"서버 연결 실패: {str(e)}")
            return False

    def disconnect_server(self):
        self.streaming_enabled = False
        self.session_id = None
        self.is_busy = False
        if self.sio.connected:
            print("[FRONT] socket disconnect requested", flush=True)
            self.sio.disconnect()

    def start_streaming(self, session_id: str):
        self.session_id = session_id
        self.streaming_enabled = True
        connected = self.connect_server()
        print(
            f"[FRONT] webcam session started - session_id={session_id}, connected={connected}",
            flush=True,
        )

    def stop_streaming(self):
        if self.streaming_enabled or self.session_id:
            print(
                f"[FRONT] webcam streaming stopped - session_id={self.session_id}",
                flush=True,
            )
        self.streaming_enabled = False
        self.session_id = None
        self.is_busy = False

    def send_frame(self, frame_np: np.ndarray):
        now = time.time()
        if now - self._last_log_at >= 1.0:
            print(
                f"[FRONT] webcam frame captured - connected={self.sio.connected}, "
                f"streaming={self.streaming_enabled}, session_id={self.session_id}",
                flush=True,
            )
            self._last_log_at = now

        if not self.streaming_enabled:
            return

        if not self.session_id:
            print("[FRONT][ERROR] frame send skipped: session_id missing", flush=True)
            return

        if not self.sio.connected:
            connected = self.connect_server()
            if not connected:
                return

        if self.is_busy:
            return

        try:
            self.is_busy = True
            print(
                f"[FRONT] webcam frame sending - session_id={self.session_id}",
                flush=True,
            )

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
            print(
                f"[FRONT] webcam frame sent - session_id={self.session_id}",
                flush=True,
            )
        except Exception as e:
            self.is_busy = False
            print(f"[FRONT][ERROR] frame send failed: {e}", flush=True)
            self.error_occurred.emit(f"프레임 전송 실패: {str(e)}")
