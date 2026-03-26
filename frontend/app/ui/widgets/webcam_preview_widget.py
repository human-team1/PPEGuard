from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.services.socket_service import SocketService
from app.services.webcam_service import WebcamService


class WebcamPreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.webcam_service = None
        self.socket_service = SocketService("http://127.0.0.1:5000")
        self.latest_detections = []

        self._init_ui()
        self._setup_socket_connections()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.image_label = QLabel("웹캠 미리보기 대기 중..")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: black; color: white; border: 1px solid #999;")
        self.image_label.setMinimumSize(320, 240)
        layout.addWidget(self.image_label)

    def _setup_socket_connections(self):
        self.socket_service.results_ready.connect(self._on_results_received)
        self.socket_service.error_occurred.connect(self._handle_error)

    @Slot(dict)
    def _on_results_received(self, data: dict):
        self.latest_detections = data.get("persons", [])

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
        self.image_label.setText("웹캠 입력이 중지되었습니다.")

    def _clear_webcam_service(self):
        self.webcam_service = None

    def _update_frame(self, qt_img: QImage):
        draw_img = qt_img.copy()
        painter = QPainter(draw_img)

        orig_w = draw_img.width()
        scale_factor = orig_w / 640.0

        for person in self.latest_detections:
            x1 = int(person["bbox"][0] * scale_factor)
            y1 = int(person["bbox"][1] * scale_factor)
            x2 = int(person["bbox"][2] * scale_factor)
            y2 = int(person["bbox"][3] * scale_factor)

            is_safe = person["is_safe"]
            color = QColor(57, 255, 20) if is_safe else QColor(255, 0, 0)
            painter.setPen(QPen(color, 2))
            painter.drawRect(x1, y1, x2 - x1, y2 - y1)
            painter.drawText(
                x1,
                y1 - 5 if y1 > 20 else y1 + 15,
                f"ID: {person['id']} {'[SAFE]' if is_safe else '[VIOLATION]'}",
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
