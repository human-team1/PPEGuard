from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt

class StatusWidget(QWidget):
    """분석 요청의 진행 상태(로딩 인디케이터, 성공/실패 텍스트)를 담당하는 UI 컴포넌트"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        status_label_header = QLabel("분석 상태:")
        status_label_header.setStyleSheet("font-weight: bold; font-size: 11px; color: #333;")
        layout.addWidget(status_label_header)
        
        self.status_label = QLabel("대기 중")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-size: 11px; color: #555; padding: 4px;")
        
        self.progress_bar = QProgressBar()
        # min/max를 둘 다 0으로 맞추면 좌우로 움직이는 애니메이션 로딩 바 동작
        self.progress_bar.setRange(0, 0) 
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximumHeight(5)
        self.progress_bar.hide()
        
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addStretch()
        
    def show_loading(self, message: str):
        self.status_label.setText(message)
        self.status_label.setStyleSheet("font-size: 11px; color: #1976D2; font-weight: bold; padding: 4px;")
        self.progress_bar.show()
        
    def show_success(self, message: str):
        self.status_label.setText(message)
        self.status_label.setStyleSheet("font-size: 11px; color: #388E3C; font-weight: bold; padding: 4px;")
        self.progress_bar.hide()
        
    def show_error(self, message: str):
        self.status_label.setText(f"오류: {message}")
        self.status_label.setStyleSheet("font-size: 11px; color: #D32F2F; font-weight: bold; padding: 4px;")
        self.progress_bar.hide()
        
    def reset(self):
        self.status_label.setText("대기 중")
        self.status_label.setStyleSheet("font-size: 11px; color: #555; padding: 4px;")
        self.progress_bar.hide()
