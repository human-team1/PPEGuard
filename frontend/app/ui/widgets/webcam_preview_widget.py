import base64
import logging

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.services.socket_service import SocketService
from app.services.webcam_service import WebcamService


logger = logging.getLogger(__name__)


class WebcamPreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.webcam_service = None
        self.socket_service = SocketService("http://127.0.0.1:5000")
        self.latest_detections = []
        self.latest_preview_image = QImage()

        self._init_ui()
        self._setup_socket_connections()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.image_label = QLabel("웹캠 미리보기를 준비 중입니다.")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: black; color: white; border: 1px solid #999;")
        self.image_label.setMinimumSize(320, 240)
        layout.addWidget(self.image_label)

    def _setup_socket_connections(self):
        self.socket_service.analysis_frame_result_ready.connect(self._on_frame_result_received)
        self.socket_service.analysis_progress_ready.connect(self._on_progress_received)
        self.socket_service.error_occurred.connect(self._handle_error)

    @Slot(dict)
    def _on_frame_result_received(self, data: dict):
        self.latest_detections = data.get("detections", [])
        preview_frame = data.get("preview_frame")
        if preview_frame:
            try:
                image_bytes = base64.b64decode(preview_frame)
                image = QImage.fromData(image_bytes, "JPG")
                if not image.isNull():
                    self.latest_preview_image = image
            except Exception as exc:
                logger.warning("[Preview] frame decode failed error=%s", exc)

        self._render_preview()

    @Slot(dict)
    def _on_progress_received(self, data: dict):
        logger.debug("[Preview] progress received session_id=%s", data.get("session_id"))

    def start_camera(self, camera_id=0):
        if self.webcam_service and self.webcam_service.isRunning():
            return

        self.stop_camera()
        self.webcam_service = WebcamService(camera_id, self, fps_limit=10)
        self.webcam_service.frame_ready.connect(self._update_frame)
        self.webcam_service.error_occurred.connect(self._handle_error)
        self.webcam_service.raw_frame_ready.connect(self.socket_service.send_frame)
        self.webcam_service.finished.connect(self._clear_webcam_service)
        self.webcam_service.stopped.connect(self._clear_webcam_service)
        self.webcam_service.start()

    def start_streaming(self, session_id: str):
        self.socket_service.start_streaming(session_id)

    def stop_streaming(self):
        self.socket_service.stop_streaming()

    def stop_camera(self):
        self.stop_streaming()

        webcam_service = self.webcam_service
        if webcam_service:
            if webcam_service.isRunning():
                webcam_service.stop()
            self._clear_webcam_service()

        self.socket_service.disconnect_server()
        self.latest_preview_image = QImage()
        self.image_label.setText("웹캠 입력이 중지되었습니다.")

    def _clear_webcam_service(self):
        self.webcam_service = None

    def _update_frame(self, qt_img: QImage):
        if self.latest_preview_image.isNull():
            self.latest_preview_image = qt_img.copy()
        self._render_preview()

    def _render_preview(self):
        if self.latest_preview_image.isNull():
            return

        draw_img = self.latest_preview_image.copy()
        painter = QPainter(draw_img)

        orig_w = max(draw_img.width(), 1)
        scale_factor = orig_w / 640.0

        for person in self.latest_detections:
            bbox = person.get("bbox", {})
            x1 = int(bbox.get("x1", 0) * scale_factor)
            y1 = int(bbox.get("y1", 0) * scale_factor)
            x2 = int(bbox.get("x2", 0) * scale_factor)
            y2 = int(bbox.get("y2", 0) * scale_factor)

            is_safe = (
                person.get("helmet_status") == "WORN"
                and person.get("vest_status") == "WORN"
            )
            color = QColor(57, 255, 20) if is_safe else QColor(255, 0, 0)
            painter.setPen(QPen(color, 2))
            painter.drawRect(x1, y1, x2 - x1, y2 - y1)
            painter.drawText(
                x1,
                y1 - 5 if y1 > 20 else y1 + 15,
                f"ID: {person.get('track_id', '-')} {'[SAFE]' if is_safe else '[VIOLATION]'}",
            )

        painter.end()

        pixmap = QPixmap.fromImage(draw_img).scaled(
            self.image_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.image_label.setPixmap(pixmap)

    def _handle_error(self, err_msg: str):
        self.image_label.setText(f"웹캠/통신 오류 발생:\n{err_msg}")
