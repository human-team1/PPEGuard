import logging

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.config.result_dashboard_config import (
    NORMAL_INCLUDED_FILTER_OPTIONS,
    OCR_CONFIRMED_FILTER_OPTIONS,
    SESSION_TABLE_COLUMNS,
    VIOLATION_FILTER_OPTIONS,
)
from app.models.dashboard_models import SessionDashboardDto
from app.services.api_client import ApiClient
from app.services.socket_service import SocketService
from app.ui.widgets.analysis_live_monitor_widget import AnalysisLiveMonitorWidget
from app.ui.widgets.dashboard_bar_chart_widget import DashboardBarChartWidget
from app.utils.async_task import ApiWorker


logger = logging.getLogger(__name__)


class ResultView(QWidget):
    def __init__(self, api_client: ApiClient, settings=None, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.settings = settings
        self.list_worker = None
        self.pending_reload = False
        self.current_session_id = None
        self.current_dashboard = None
        self.pending_source_type = None
        self.current_analysis_status = None
        self.has_received_segment_saved = False
        self.active_inspection_items = (
            settings.get_selected_inspection_items() if settings else ["helmet", "vest"]
        )
        self.visible_column_keys = (
            settings.get_visible_result_columns()
            if settings
            else [item["key"] for item in SESSION_TABLE_COLUMNS if item["default_visible"]]
        )
        self.socket_service = SocketService(self.api_client.base_url)
        self.segment_sync_timer = QTimer(self)
        self.segment_sync_timer.setInterval(3000)
        self.segment_sync_timer.timeout.connect(self._sync_segments_fallback)
        self._init_ui()
        self._connect_live_events()
        self.set_active_inspection_items(self.active_inspection_items)
        self._set_dashboard_visible(False)

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setSpacing(10)

        title_layout = QHBoxLayout()
        title = QLabel("세션 결과 화면")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title_layout.addWidget(title)
        title_layout.addStretch()

        self.column_menu_button = QToolButton()
        self.column_menu_button.setText("컬럼 선택")
        self.column_menu_button.setPopupMode(QToolButton.InstantPopup)
        self.column_menu_button.setMenu(self._build_column_menu())
        title_layout.addWidget(self.column_menu_button)

        self.refresh_btn = QPushButton("결과 새로고침")
        self.refresh_btn.clicked.connect(lambda: self.load_results(reason="manual"))
        title_layout.addWidget(self.refresh_btn)
        root_layout.addLayout(title_layout)

        self.filter_bar = QWidget(self)
        filter_layout = QHBoxLayout(self.filter_bar)
        filter_layout.setContentsMargins(0, 0, 0, 0)

        filter_layout.addWidget(QLabel("위반 유형", self.filter_bar))
        self.violation_combo = QComboBox(self.filter_bar)
        for option in VIOLATION_FILTER_OPTIONS:
            self.violation_combo.addItem(option["label"], option["key"])
        self.violation_combo.currentIndexChanged.connect(self._apply_cached_dashboard)
        filter_layout.addWidget(self.violation_combo)

        filter_layout.addWidget(QLabel("직원 ID", self.filter_bar))
        self.employee_id_input = QLineEdit(self.filter_bar)
        self.employee_id_input.setPlaceholderText("직원 ID 포함 검색")
        self.employee_id_input.textChanged.connect(self._apply_cached_dashboard)
        filter_layout.addWidget(self.employee_id_input)

        filter_layout.addWidget(QLabel("OCR 번호", self.filter_bar))
        self.ocr_number_input = QLineEdit(self.filter_bar)
        self.ocr_number_input.setPlaceholderText("OCR 번호 포함 검색")
        self.ocr_number_input.textChanged.connect(self._apply_cached_dashboard)
        filter_layout.addWidget(self.ocr_number_input)

        filter_layout.addWidget(QLabel("OCR 확정", self.filter_bar))
        self.ocr_confirmed_combo = QComboBox(self.filter_bar)
        for option in OCR_CONFIRMED_FILTER_OPTIONS:
            self.ocr_confirmed_combo.addItem(option["label"], option["key"])
        self.ocr_confirmed_combo.currentIndexChanged.connect(self._apply_cached_dashboard)
        filter_layout.addWidget(self.ocr_confirmed_combo)

        filter_layout.addWidget(QLabel("정상 포함", self.filter_bar))
        self.normal_included_combo = QComboBox(self.filter_bar)
        for option in NORMAL_INCLUDED_FILTER_OPTIONS:
            self.normal_included_combo.addItem(option["label"], option["key"])
        self.normal_included_combo.currentIndexChanged.connect(self._apply_cached_dashboard)
        filter_layout.addWidget(self.normal_included_combo)
        root_layout.addWidget(self.filter_bar)

        self.live_monitor = AnalysisLiveMonitorWidget(self)
        root_layout.addWidget(self.live_monitor)

        self.empty_label = QLabel(
            "세션 시작 전입니다. 분석을 시작하면 저장된 세그먼트 결과가 여기에 표시됩니다.",
            self,
        )
        self.empty_label.setStyleSheet("font-size: 13px; color: #666; padding: 16px;")
        root_layout.addWidget(self.empty_label)

        self.dashboard_container = QWidget(self)
        dashboard_layout = QVBoxLayout(self.dashboard_container)
        dashboard_layout.setContentsMargins(0, 0, 0, 0)
        dashboard_layout.setSpacing(10)

        self.chart_container = QWidget(self.dashboard_container)
        self.chart_layout = QHBoxLayout(self.chart_container)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        dashboard_layout.addWidget(self.chart_container)

        self.table = QTableWidget(self.dashboard_container)
        self.table.setColumnCount(len(SESSION_TABLE_COLUMNS))
        self.table.setHorizontalHeaderLabels(
            [column["label"] for column in SESSION_TABLE_COLUMNS]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        dashboard_layout.addWidget(self.table, stretch=1)

        root_layout.addWidget(self.dashboard_container, stretch=1)
        self._apply_column_visibility()

    def _connect_live_events(self):
        self.socket_service.analysis_session_status_changed.connect(
            self._on_analysis_session_status
        )
        self.socket_service.analysis_progress_ready.connect(
            self.live_monitor.handle_progress
        )
        self.socket_service.analysis_frame_result_ready.connect(
            self.live_monitor.handle_frame_result
        )
        self.socket_service.analysis_segment_saved.connect(
            self._on_analysis_segment_saved
        )
        self.socket_service.error_occurred.connect(self._on_live_socket_error)

    def ensure_live_connection(self):
        self.socket_service.server_url = self.api_client.base_url
        return self.socket_service.ensure_connected()

    def prepare_live_session(self, source_type: str):
        self.pending_source_type = source_type
        self.current_session_id = None
        self.current_dashboard = None
        self.pending_reload = False
        self.current_analysis_status = None
        self.has_received_segment_saved = False
        self.segment_sync_timer.stop()
        self.live_monitor.prepare_session(source_type)
        self._set_dashboard_visible(False)
        self.empty_label.setVisible(True)
        self.empty_label.setText(
            "세션이 아직 시작되지 않았습니다. 세그먼트가 저장되면 결과가 자동으로 표시됩니다."
        )

    def set_session_id(self, session_id: str):
        self.current_session_id = session_id
        self.live_monitor.set_session_id(session_id)

    def set_active_inspection_items(self, item_keys: list[str]):
        self.active_inspection_items = list(item_keys)
        self.live_monitor.set_active_items(item_keys)
        self._apply_column_visibility()
        if self.current_dashboard is not None:
            self._apply_cached_dashboard()

    def load_results(self, reason: str = "manual"):
        if self.list_worker and self.list_worker.isRunning():
            self.pending_reload = True
            return
        if not self.current_session_id:
            self._set_dashboard_visible(False)
            self.empty_label.setVisible(True)
            self.empty_label.setText("현재 선택된 세션이 없습니다.")
            return

        self.pending_reload = False
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("불러오는 중..")
        timeout_sec = 15 if self._is_processing_video_session() else 5
        logger.debug(
            "[ResultView] load_results reason=%s session_id=%s timeout=%s",
            reason,
            self.current_session_id,
            timeout_sec,
        )
        self.list_worker = ApiWorker(
            self.api_client.get_session_segments,
            session_id=self.current_session_id,
            timeout_sec=timeout_sec,
        )
        self.list_worker.result_ready.connect(self._on_dashboard_loaded)
        self.list_worker.error_occurred.connect(self._on_dashboard_error)
        self.list_worker.finished.connect(self._clear_list_worker)
        self.list_worker.start()

    def _on_dashboard_loaded(self, raw_data: dict):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("결과 새로고침")
        self.live_monitor.sync_from_segments_response(raw_data)
        self.current_dashboard = SessionDashboardDto.from_segments_api(
            raw_data,
            active_items=self.active_inspection_items,
        )
        self._apply_cached_dashboard()

    def _on_dashboard_error(self, err_msg: str):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("결과 새로고침")
        if self._should_suppress_results_error(err_msg):
            logger.debug(
                "[ResultView] results timeout suppressed session_id=%s status=%s",
                self.current_session_id,
                self.current_analysis_status,
            )
            if self.current_dashboard is None:
                self._set_dashboard_visible(False)
                self.empty_label.setVisible(True)
            self.empty_label.setText("결과 준비 중입니다. 자동 갱신 중입니다.")
            return
        QMessageBox.warning(self, "세션 결과 조회 오류", err_msg)

    def _apply_cached_dashboard(self):
        if self.current_dashboard is None:
            self._set_dashboard_visible(False)
            return

        dashboard = SessionDashboardDto.from_segments_api(
            {
                "session_id": self.current_dashboard.session_id,
                "segments": self.current_dashboard.source_segments,
            },
            filters=self._collect_filters(),
            active_items=self.active_inspection_items,
        )
        self._render_dashboard(dashboard)

    def _render_dashboard(self, dashboard: SessionDashboardDto):
        has_rows = bool(dashboard.rows)
        self._set_dashboard_visible(has_rows)
        self.empty_label.setVisible(not has_rows)
        if not has_rows:
            self.empty_label.setText(
                "저장된 세그먼트 결과가 아직 없거나 필터 조건에 맞는 결과가 없습니다."
            )

        self._render_charts(dashboard)
        self._fill_table(dashboard)

    def _render_charts(self, dashboard: SessionDashboardDto):
        self._clear_layout(self.chart_layout)

        segment_chart = DashboardBarChartWidget(
            "세그먼트별 위반 수",
            parent=self.chart_container,
        )
        segment_chart.set_series(dashboard.segment_violation_counts)
        self.chart_layout.addWidget(segment_chart)

        status_chart = DashboardBarChartWidget(
            "상태별 비율",
            parent=self.chart_container,
        )
        status_chart.set_series(dashboard.status_ratio)
        self.chart_layout.addWidget(status_chart)

    def _fill_table(self, dashboard: SessionDashboardDto):
        self.table.setRowCount(len(dashboard.rows))
        for row_index, row in enumerate(dashboard.rows):
            row_map = {
                "segment_label": row.segment_label,
                "reference_time": row.reference_time,
                "employee_id": row.employee_id,
                "ocr_number": row.ocr_number,
                "ocr_confirmed": row.ocr_confirmed,
                "helmet_status": row.helmet_status,
                "vest_status": row.vest_status,
                "overall_ppe_status": row.overall_ppe_status,
                "violation_type": row.violation_type,
            }
            for col_index, column in enumerate(SESSION_TABLE_COLUMNS):
                self.table.setItem(
                    row_index,
                    col_index,
                    QTableWidgetItem(row_map.get(column["key"], "")),
                )
        self._apply_column_visibility()

    def _collect_filters(self):
        return {
            "violation_type": self.violation_combo.currentData(),
            "employee_id": self.employee_id_input.text(),
            "ocr_number": self.ocr_number_input.text(),
            "ocr_confirmed": self.ocr_confirmed_combo.currentData(),
            "normal_included": self.normal_included_combo.currentData(),
        }

    def _build_column_menu(self):
        menu = QMenu(self)
        for column in SESSION_TABLE_COLUMNS:
            action = menu.addAction(column["label"])
            action.setCheckable(True)
            action.setChecked(column["key"] in self.visible_column_keys)
            action.toggled.connect(
                lambda checked, key=column["key"]: self._toggle_column_visibility(key, checked)
            )
        return menu

    def _toggle_column_visibility(self, key: str, checked: bool):
        if checked and key not in self.visible_column_keys:
            self.visible_column_keys.append(key)
        if not checked and key in self.visible_column_keys:
            self.visible_column_keys.remove(key)
        if self.settings:
            self.settings.save_visible_result_columns(self.visible_column_keys)
        self._apply_column_visibility()

    def _apply_column_visibility(self):
        active_set = set(self.active_inspection_items)
        for col_index, column in enumerate(SESSION_TABLE_COLUMNS):
            hidden = column["key"] not in self.visible_column_keys
            if column["key"] == "helmet_status" and "helmet" not in active_set:
                hidden = True
            if column["key"] == "vest_status" and "vest" not in active_set:
                hidden = True
            self.table.setColumnHidden(col_index, hidden)

    def _set_dashboard_visible(self, visible: bool):
        self.filter_bar.setVisible(visible)
        self.dashboard_container.setVisible(visible)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)

    def _sync_segments_fallback(self):
        if not self.has_received_segment_saved:
            return
        if self.current_session_id and not (self.list_worker and self.list_worker.isRunning()):
            self.load_results(reason="fallback")

    def _on_analysis_session_status(self, payload: dict):
        source_type = payload.get("source_type")
        session_id = payload.get("session_id")
        self.live_monitor.handle_session_status(payload)
        if not self.current_session_id and self.pending_source_type == source_type:
            self.set_session_id(session_id)

        status = payload.get("status")
        self.current_analysis_status = status
        if status in {"started", "processing"} and self.current_session_id == session_id:
            if self.has_received_segment_saved and not self.segment_sync_timer.isActive():
                self.segment_sync_timer.start()
        if status in {"completed", "failed", "stopping"}:
            self.segment_sync_timer.stop()
        if status in {"completed", "failed"} and self.current_session_id == session_id:
            self.load_results(reason=f"session_status:{status}")

    def _on_analysis_segment_saved(self, payload: dict):
        self.live_monitor.handle_segment_saved(payload)
        if payload.get("session_id") == self.current_session_id:
            self.has_received_segment_saved = True
            if (
                self.current_analysis_status in {"started", "processing"}
                and not self.segment_sync_timer.isActive()
            ):
                self.segment_sync_timer.start()
            self.load_results(reason="segment_saved")

    def _on_live_socket_error(self, err_msg: str):
        self.live_monitor.handle_session_status(
            {
                "session_id": self.current_session_id,
                "source_type": self.pending_source_type,
                "status": "failed",
            }
        )
        self.segment_sync_timer.stop()
        self.live_monitor._append_event(f"소켓 오류: {err_msg}")

    def _clear_list_worker(self):
        self.list_worker = None
        if self.pending_reload:
            self.pending_reload = False
            self.load_results(reason="pending_reload")

    def _is_processing_video_session(self) -> bool:
        return (
            self.pending_source_type == "VIDEO_FILE"
            and self.current_analysis_status in {"started", "processing"}
        )

    def _should_suppress_results_error(self, err_msg: str) -> bool:
        is_timeout = "응답 시간 초과" in err_msg or "timeout" in err_msg.lower()
        return is_timeout and self._is_processing_video_session()
