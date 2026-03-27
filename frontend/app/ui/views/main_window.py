from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from app.config.settings import AppSettings
from app.services.api_client import ApiClient
from app.ui.views.result_view import ResultView
from app.ui.widgets.input_selection_widget import InputSelectionWidget
from app.ui.widgets.server_config_widget import ServerConfigWidget
from app.ui.widgets.status_widget import StatusWidget
from app.utils.async_task import ApiWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PPE Guard - Desktop Client")
        self.resize(1200, 760)

        self.settings = AppSettings()
        self.api_client = ApiClient(self.settings.get_server_url())
        self.session_worker = None
        self.stop_worker = None
        self.current_session_id = None
        self.current_state = "대기"

        self._init_ui()
        self._apply_analysis_state("대기", "분석을 시작할 준비가 되었습니다.")

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)

        title_label = QLabel("PPE Guard 영상 분석 데스크톱")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; margin: 5px;")
        main_layout.addWidget(title_label)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(8)

        selected_items = self.settings.get_selected_inspection_items()
        self.server_widget = ServerConfigWidget(self.settings, self.api_client)
        self.input_widget = InputSelectionWidget(selected_item_keys=selected_items)
        self.status_widget = StatusWidget()
        self.result_view = ResultView(self.api_client, settings=self.settings)
        self.result_view.set_active_inspection_items(selected_items)

        self.server_widget.connection_status_changed.connect(
            self.input_widget.set_server_connected
        )
        self.input_widget.set_server_connected(False)
        self.input_widget.analysis_requested.connect(self._handle_analysis_request)
        self.input_widget.analysis_stop_requested.connect(self._handle_stop_request)
        self.input_widget.inspection_items_changed.connect(
            self._on_inspection_items_changed
        )
        self.input_widget.source_type_changed.connect(
            self.result_view.set_input_source_type
        )

        left_layout.addWidget(self.server_widget)
        left_layout.addWidget(self.input_widget, stretch=1)
        left_layout.addWidget(self.status_widget)

        content_layout.addWidget(left_panel, stretch=1)
        content_layout.addWidget(self.result_view, stretch=2)
        main_layout.addLayout(content_layout, stretch=1)

        self.statusBar().showMessage("대기")
        self.result_view.set_input_source_type(
            self.input_widget.get_current_source_type()
        )
        QTimer.singleShot(
            0,
            lambda: self.result_view.set_input_source_type(
                self.input_widget.get_current_source_type()
            ),
        )

    def _apply_analysis_state(self, state: str, message: str | None = None):
        self.current_state = state
        detail = message or state
        self.input_widget.set_analysis_state(state, detail)
        self.status_widget.set_analysis_state(state, detail)
        self.statusBar().showMessage(detail)

    def _handle_analysis_request(
        self,
        source_type: str,
        source_val: str,
        video_started_at=None,
        inspection_item_keys: list[str] | None = None,
    ):
        if self.session_worker and self.session_worker.isRunning():
            self._apply_analysis_state(
                "실패",
                "이미 요청 처리 중입니다. 잠시 후 다시 시도해주세요.",
            )
            return

        self.result_view.prepare_live_session(source_type)
        self.result_view.ensure_live_connection()

        if source_type == "VIDEO_FILE":
            self._apply_analysis_state(
                "시작 요청중",
                "영상 업로드 및 분석 시작을 요청했습니다.",
            )
            self.session_worker = ApiWorker(
                self.api_client.upload_video,
                video_path=source_val,
                video_started_at=video_started_at,
                inspection_item_keys=inspection_item_keys or [],
            )
            self.session_worker.result_ready.connect(self._on_video_uploaded)
            self._apply_analysis_state(
                "분석중",
                "영상 업로드 중이며 분석이 시작되었습니다.",
            )
        else:
            self._apply_analysis_state(
                "시작 요청중",
                "웹캠 분석 세션 생성을 요청했습니다.",
            )
            self.session_worker = ApiWorker(
                self.result_view.socket_service.start_webcam_analysis,
                "Webcam-Live",
                3,
            )
            self.session_worker.result_ready.connect(self._on_session_started)

        self.session_worker.error_occurred.connect(self._on_session_error)
        self.session_worker.finished.connect(self.session_worker.deleteLater)
        self.session_worker.finished.connect(self._clear_session_worker)
        self.session_worker.start()

    def _handle_stop_request(self):
        if self.current_state != "분석중":
            return

        is_video_mode = self.input_widget.radio_file.isChecked()
        if not is_video_mode and not self.current_session_id:
            return

        reply = QMessageBox.question(
            self,
            "분석 중단 확인",
            "정말로 분석을 중단하시겠습니까?\n진행 중인 분석 결과가 삭제됩니다.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.No:
            return

        if self.stop_worker and self.stop_worker.isRunning():
            return

        self._apply_analysis_state("종료 요청중", "분석 종료를 요청했습니다.")

        if self.input_widget.radio_file.isChecked():
            self.stop_worker = ApiWorker(
                self.api_client.stop_video_analysis,
                self.current_session_id,
            )
        else:
            self.stop_worker = ApiWorker(
                self.result_view.socket_service.stop_webcam_analysis,
                self.current_session_id,
            )
        self.stop_worker.result_ready.connect(self._on_stop_completed)
        self.stop_worker.error_occurred.connect(self._on_stop_error)
        self.stop_worker.finished.connect(self.stop_worker.deleteLater)
        self.stop_worker.finished.connect(self._clear_stop_worker)
        self.stop_worker.start()

    def _on_video_uploaded(self, payload: dict):
        if not payload or not isinstance(payload, dict):
            self._apply_analysis_state("실패", "서버 응답이 올바르지 않습니다.")
            return

        self.current_session_id = payload.get("session_id")
        message = payload.get("message", "동영상 분석이 완료되었습니다.")

        if self.current_session_id:
            self.result_view.set_session_id(self.current_session_id)

        self._apply_analysis_state("완료", message)
        self.result_view.set_input_source_type(
            self.input_widget.get_current_source_type()
        )
        self.result_view.load_results()

    def _on_session_started(self, payload: dict):
        session_id = payload.get("session_id")
        status = payload.get("status", "Unknown")

        if not session_id:
            self._apply_analysis_state("실패", "session_id를 받지 못했습니다.")
            return

        self.current_session_id = session_id
        self.result_view.set_session_id(session_id)
        self._apply_analysis_state(
            "분석중",
            f"세션 [{session_id[:8]}] 분석중 - 상태: {status}",
        )

    def _on_stop_completed(self, payload: dict):
        self._apply_analysis_state("중지", "분석을 중지했습니다.")
        if payload.get("session_id"):
            self.result_view.set_session_id(payload.get("session_id"))
        self.result_view.set_input_source_type(
            self.input_widget.get_current_source_type()
        )
        if self.input_widget.get_current_source_type() == "VIDEO_FILE":
            self.result_view.load_results()

    def _on_stop_error(self, err_msg: str):
        self._apply_analysis_state("실패", err_msg)

    def _on_session_error(self, err_msg: str):
        self._apply_analysis_state("실패", err_msg)

    def _on_inspection_items_changed(self, selected_keys: list[str]):
        self.settings.save_selected_inspection_items(selected_keys)
        self.result_view.set_active_inspection_items(selected_keys)
        selected_text = ", ".join(selected_keys) if selected_keys else "선택 없음"
        self.statusBar().showMessage(f"점검 항목 설정 변경: {selected_text}")

    def _clear_session_worker(self):
        if not hasattr(self, "_past_workers"):
            self._past_workers = []

        if self.session_worker:
            self._past_workers.append(self.session_worker)
            self.session_worker = None

    def _clear_stop_worker(self):
        if not hasattr(self, "_past_workers"):
            self._past_workers = []

        if self.stop_worker:
            self._past_workers.append(self.stop_worker)
            self.stop_worker = None

    def closeEvent(self, event):
        if hasattr(self, "result_view"):
            self.result_view.begin_shutdown()
        if self.session_worker and self.session_worker.isRunning():
            self.session_worker.wait(2000)
        if self.stop_worker and self.stop_worker.isRunning():
            self.stop_worker.wait(2000)
        if (
            hasattr(self, "result_view")
            and self.result_view.list_worker
            and self.result_view.list_worker.isRunning()
        ):
            self.result_view.list_worker.wait(2000)

        if hasattr(self, "result_view"):
            self.result_view.socket_service.disconnect_server()

        event.accept()
