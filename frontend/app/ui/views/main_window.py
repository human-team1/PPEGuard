import os
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel
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
        self.resize(1200, 700)

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

        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(8)

        self.server_widget = ServerConfigWidget(self.settings, self.api_client)
        self.input_widget = InputSelectionWidget()
        self.status_widget = StatusWidget()

        self.server_widget.connection_status_changed.connect(
            self.input_widget.set_server_connected
        )
        self.input_widget.set_server_connected(False)
        self.input_widget.analysis_requested.connect(self._handle_analysis_request)

        left_layout.addWidget(self.server_widget)
        left_layout.addWidget(self.input_widget, stretch=1)
        left_layout.addWidget(self.status_widget)

        self.result_view = ResultView(self.api_client)

        content_layout.addWidget(left_panel, stretch=1)
        content_layout.addWidget(self.result_view, stretch=2)

        main_layout.addLayout(content_layout, stretch=1)

    def _handle_analysis_request(self, source_type: str, source_val: str):
        self.input_widget.start_btn.setEnabled(False)

        if source_type == "VIDEO_FILE":
            self.status_widget.show_loading("동영상 업로드를 요청 중입니다...")

            self.worker = ApiWorker(
                self.api_client.upload_video,
                video_path=source_val
            )
            self.worker.result_ready.connect(self._on_video_uploaded)
            self.worker.error_occurred.connect(self._on_session_error)
            self.worker.start()
            return

        # (qthread)[Bug Fix] 이미 워커가 작동 중이면 중복 실행 방지 및 안전하게 해제
        if self.worker and self.worker.isRunning():
            print("[GUI] 기존 작업이 아직 실행 중입니다. 대기 혹은 종료 처리합니다.")
            self.worker.wait(1000) # 안전을 위해 1초 대기

        self.status_widget.show_loading("분석 세션 생성을 요청 중입니다...")

        source_name = "Webcam-Live"
        self.worker = ApiWorker(
            self.api_client.start_session,
            source_type=source_type,
            source_name=source_name,
            frame_interval=3
        )
        self.worker.result_ready.connect(self._on_session_started)
        self.worker.error_occurred.connect(self._on_session_error)
        self.worker.start()

    def _on_video_uploaded(self, payload: dict):
        message = payload.get("message", "동영상 업로드 완료")
        self.status_widget.show_success(message)
        self.input_widget.start_btn.setEnabled(True)
        self.result_view.load_results()

    def _on_session_started(self, payload: dict):
        session_id = payload.get("session_id", "Unknown")
        status = payload.get("status", "Unknown")

        self.status_widget.show_success(f"생성 완료: [{session_id[:8]}] - 상태: {status}")
        self.input_widget.start_btn.setEnabled(True)
        
        # [Step 2 지원] 웹캠 소켓 서비스에 세션 ID 주입
        if hasattr(self.input_widget, 'webcam_preview'):
            self.input_widget.webcam_preview.socket_service.session_id = session_id
            
        self.result_view.load_results()

    def _on_session_error(self, err_msg: str):
        self.status_widget.show_error(err_msg)
        self.input_widget.start_btn.setEnabled(True)

    def closeEvent(self, event):
        """앱 종료 시 백그라운드 웹캠/API 스레드를 안전하게 해제 (Zombie 방지)"""
        if self.worker and self.worker.isRunning():
            self.worker.wait(1000)

        if hasattr(self, "input_widget") and hasattr(self.input_widget, "webcam_preview"):
            self.input_widget.webcam_preview.stop_camera()

        event.accept()
        