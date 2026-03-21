import os
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QTabWidget
from PySide6.QtCore import Qt
from app.config.settings import AppSettings
from app.services.api_client import ApiClient
from app.ui.widgets.server_config_widget import ServerConfigWidget
from app.ui.widgets.input_selection_widget import InputSelectionWidget
from app.ui.widgets.status_widget import StatusWidget
from app.utils.async_task import ApiWorker
from app.ui.views.result_view import ResultView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PPE Guard - Desktop Client")
        self.resize(800, 650)
        
        self.settings = AppSettings()
        self.api_client = ApiClient(self.settings.get_server_url())
        self.worker = None 
        
        self._init_ui()
        
    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        
        title_label = QLabel("PPE Guard 영상 분석 시스템")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; margin: 5px;")
        main_layout.addWidget(title_label)
        
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 1. 탭 1: 분석 요청 뷰
        req_widget = QWidget()
        req_layout = QVBoxLayout(req_widget)
        
        self.server_widget = ServerConfigWidget(self.settings, self.api_client)
        self.input_widget = InputSelectionWidget()
        self.status_widget = StatusWidget()
        
        self.server_widget.connection_status_changed.connect(
            self.input_widget.set_server_connected
        )
        self.input_widget.set_server_connected(False)
        self.input_widget.analysis_requested.connect(self._handle_analysis_request)
        
        req_layout.addWidget(self.server_widget)
        req_layout.addWidget(self.input_widget, stretch=1)
        req_layout.addWidget(self.status_widget)
        self.tab_widget.addTab(req_widget, "1. 분석 요청")
        
        # 2. 탭 2: 결과 조회 뷰
        self.result_view = ResultView(self.api_client)
        self.tab_widget.addTab(self.result_view, "2. 통합 결과 조회")
        
    def _handle_analysis_request(self, source_type: str, source_val: str):
        self.status_widget.show_loading("분석 세션 생성을 요청 중입니다...")
        self.input_widget.start_btn.setEnabled(False)
        
        source_name = "Webcam-Live"
        if source_type == "VIDEO_FILE":
            source_name = os.path.basename(source_val)
            
        self.worker = ApiWorker(
            self.api_client.start_session,
            source_type=source_type,
            source_name=source_name,
            frame_interval=3 
        )
        self.worker.result_ready.connect(self._on_session_started)
        self.worker.error_occurred.connect(self._on_session_error)
        self.worker.start()
        
    def _on_session_started(self, payload: dict):
        session_id = payload.get("session_id", "Unknown")
        status = payload.get("status", "Unknown")
        
        self.status_widget.show_success(f"생성 완료: [{session_id[:8]}] - 상태: {status}")
        self.input_widget.start_btn.setEnabled(True)
        
        # 3단계 로직 적용: 성공 시 결과 조회 탭으로 자동 이동하고 목록 새로고침 발생
        self.tab_widget.setCurrentIndex(1)
        self.result_view.load_results()
        
    def _on_session_error(self, err_msg: str):
        self.status_widget.show_error(err_msg)
        self.input_widget.start_btn.setEnabled(True)

    def closeEvent(self, event):
        """앱 종료 시 백그라운드 웹캠/API 스레드를 안전하게 해제 (Zombie 방지)"""
        if self.worker and self.worker.isRunning():
            self.worker.wait(1000) 
        
        if hasattr(self, 'input_widget') and hasattr(self.input_widget, 'webcam_preview'):
            self.input_widget.webcam_preview.stop_camera()
            
        event.accept()
