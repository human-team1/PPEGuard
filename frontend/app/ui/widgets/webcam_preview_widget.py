from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt
from app.services.webcam_service import WebcamService

class WebcamPreviewWidget(QWidget):
    """웹캠의 프레임을 QLabel 상에 전시하는 전용 UI 위젯"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.webcam_service = None
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.image_label = QLabel("비디오 미리보기 컨테이너 유휴 상태...")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: black; color: white; border: 1px solid #999;")
        self.image_label.setMinimumSize(320, 240)
        
        layout.addWidget(self.image_label)
        
    def start_camera(self, camera_id=0):
        self.stop_camera()
        self.webcam_service = WebcamService(camera_id, self)
        self.webcam_service.frame_ready.connect(self._update_frame)
        self.webcam_service.error_occurred.connect(self._handle_error)
        self.webcam_service.start()
        
    def stop_camera(self):
        if self.webcam_service and self.webcam_service.isRunning():
            self.webcam_service.stop()
            self.webcam_service = None
            self.image_label.setText("웹캠 입력을 중지했습니다.")
            
    def _update_frame(self, qt_img: QImage):
        # QLabel 크기에 맞춰 이미지 해상도를 비율 유지하며 조절
        pixmap = QPixmap.fromImage(qt_img).scaled(
            self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.image_label.setPixmap(pixmap)
        
    def _handle_error(self, err_msg: str):
        self.image_label.setText(f"비디오 에러 발생:\n{err_msg}")
