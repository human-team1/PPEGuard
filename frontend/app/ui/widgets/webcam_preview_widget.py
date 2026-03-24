from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, QColor
from PySide6.QtCore import Qt, Slot
from app.services.webcam_service import WebcamService
from app.services.socket_service import SocketService

class WebcamPreviewWidget(QWidget):
    """
    [최종 완성: 5000 포트 기반 AI 실시간 분석 위젯]
    - WebSocket 실시간 스트리밍
    - 640px 좌표 보정 (Re-scaling)
    - 140ms 수준의 지연 없는 바운딩 박스 오버레이
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.webcam_service = None
        
        # [최종: 5000 포트로 통일]
        self.socket_service = SocketService("http://127.0.0.1:5000")
        self.latest_detections = [] 
        
        self._init_ui()
        self._setup_socket_connections()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.image_label = QLabel("비디오 미리보기 컨테이너 유휴 상태...")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: black; color: white; border: 1px solid #999;")
        self.image_label.setMinimumSize(320, 240)
        
        layout.addWidget(self.image_label)

    def _setup_socket_connections(self):
        self.socket_service.results_ready.connect(self._on_results_received)
        self.socket_service.error_occurred.connect(self._handle_error)

    @Slot(dict)
    def _on_results_received(self, data: dict):
        self.latest_detections = data.get('persons', [])

    def start_camera(self, camera_id=0):
        self.stop_camera()
        self.socket_service.connect_server()
        
        # [최적화: AI 분석 간격(fps_limit) 조절 가능]
        self.webcam_service = WebcamService(camera_id, self, fps_limit=10)
        self.webcam_service.frame_ready.connect(self._update_frame)
        self.webcam_service.error_occurred.connect(self._handle_error)
        self.webcam_service.raw_frame_ready.connect(self.socket_service.send_frame)
        
        self.webcam_service.start()
        
    def stop_camera(self):
        if self.webcam_service and self.webcam_service.isRunning():
            self.webcam_service.stop()
            self.webcam_service = None
            
        self.socket_service.disconnect_server()
        self.image_label.setText("웹캠 입력을 중지했습니다.")
            
    def _update_frame(self, qt_img: QImage):
        """
        [완성: 수신된 실시간 AI 탐지 결과를 화면상에 정확히 오버레이]
        """
        draw_img = qt_img.copy()
        painter = QPainter(draw_img)
        
        # [좌표 보정: 640px 기준 결과를 원본 해상도(orig_w)에 맞춰 스케일링]
        orig_w = draw_img.width()
        scale_factor = orig_w / 640.0 

        for p in self.latest_detections:
            x1 = int(p['bbox'][0] * scale_factor)
            y1 = int(p['bbox'][1] * scale_factor)
            x2 = int(p['bbox'][2] * scale_factor)
            y2 = int(p['bbox'][3] * scale_factor)
            
            is_safe = p['is_safe']
            color = QColor(57, 255, 20) if is_safe else QColor(255, 0, 0)
            pen = QPen(color, 2)
            painter.setPen(pen)
            
            painter.drawRect(x1, y1, x2 - x1, y2 - y1)
            # 텍스트 오버레이
            painter.drawText(x1, y1 - 5 if y1 > 20 else y1 + 15, f"ID: {p['id']} {'[SAFE]' if is_safe else '[VIOLATION]'}")
        
        painter.end()

        # QLabel 크기에 맞춰 이미지 해상도를 조절 (유동적 크기 지원)
        pixmap = QPixmap.fromImage(draw_img).scaled(
            self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.image_label.setPixmap(pixmap)
        
    def _handle_error(self, err_msg: str):
        self.image_label.setText(f"비디오/통신 에러 발생:\n{err_msg}")
