import logging

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.api_client import ApiClient
from app.services.socket_service import SocketService
from app.ui.widgets.analysis_live_monitor_widget import AnalysisLiveMonitorWidget
from app.ui.widgets.segment_detail_widget import SegmentDetailWidget
from app.ui.widgets.track_detail_widget import TrackDetailWidget
from app.utils.async_task import ApiWorker


logger = logging.getLogger(__name__)


class ResultView(QWidget):
    def __init__(self, api_client: ApiClient, settings=None, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.settings = settings

        self.session_list_worker = None
        self.segment_worker = None
        self.list_worker = None

        self.pending_reload = False
        self._is_shutting_down = False
        self._is_loading_sessions = False
        self._is_loading_segments = False
        self._live_events_connected = False
        self._last_completed_session_id = None
        self._socket_connection_state = "disconnected"

        self.current_input_source = "VIDEO_FILE"
        self.selected_session_source_type = None
        self.is_query_panel_active = True
        self.current_query_kind = "segments"

        self.current_session_id = None
        self.current_analysis_status = None
        self.has_received_segment_saved = False
        self.selected_session_payload = None
        self.loaded_sessions: list[dict] = []
        self.loaded_segments: list[dict] = []
        self.loaded_tracks: list[dict] = []

        self.socket_service = SocketService(self.api_client.base_url)
        self.segment_sync_timer = QTimer(self)
        self.segment_sync_timer.setInterval(3000)
        self.segment_sync_timer.timeout.connect(self._sync_segments_fallback)

        self._init_ui()
        self._connect_live_events()
        self.set_input_source_type("VIDEO_FILE")

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(10)

        title_layout = QHBoxLayout()
        title = QLabel("세션 결과 조회")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.refresh_btn = QPushButton("목록 새로고침")
        self.refresh_btn.clicked.connect(self._reload_all)
        title_layout.addWidget(title)
        title_layout.addStretch()
        title_layout.addWidget(self.refresh_btn)
        root_layout.addLayout(title_layout)

        self.live_container = QWidget(self)
        live_layout = QVBoxLayout(self.live_container)
        live_layout.setContentsMargins(0, 0, 0, 0)
        live_layout.setSpacing(0)

        self.live_monitor = AnalysisLiveMonitorWidget(self.live_container)
        self.live_monitor.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        live_layout.addWidget(self.live_monitor)
        live_layout.addStretch()
        root_layout.addWidget(self.live_container, stretch=1)

        self.query_container = QWidget(self)
        query_layout = QVBoxLayout(self.query_container)
        query_layout.setContentsMargins(0, 0, 0, 0)

        self.splitter = QSplitter(self.query_container)
        query_layout.addWidget(self.splitter, stretch=1)

        session_panel = QWidget(self.query_container)
        session_layout = QVBoxLayout(session_panel)
        session_layout.setContentsMargins(0, 0, 0, 0)
        session_layout.addWidget(QLabel("세션 목록"))
        self.session_table = QTableWidget(self.query_container)
        self.session_table.setColumnCount(4)
        self.session_table.setHorizontalHeaderLabels(["세션 번호", "입력 타입", "상태", "생성 시각"])
        self.session_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.session_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.session_table.currentCellChanged.connect(self._on_session_cell_changed)
        session_layout.addWidget(self.session_table)
        self.splitter.addWidget(session_panel)

        item_panel = QWidget(self.query_container)
        item_layout = QVBoxLayout(item_panel)
        item_layout.setContentsMargins(0, 0, 0, 0)
        self.item_list_label = QLabel("세그먼트 목록")
        item_layout.addWidget(self.item_list_label)
        self.segment_table = QTableWidget(self.query_container)
        self.segment_table.setColumnCount(5)
        self.segment_table.itemSelectionChanged.connect(self._on_result_item_selected)
        item_layout.addWidget(self.segment_table)
        self.splitter.addWidget(item_panel)

        self.detail_stack = QStackedWidget(self.query_container)
        self.segment_detail_widget = SegmentDetailWidget(self.query_container)
        self.track_detail_widget = TrackDetailWidget(self.query_container)
        self.detail_stack.addWidget(self.segment_detail_widget)
        self.detail_stack.addWidget(self.track_detail_widget)
        self.splitter.addWidget(self.detail_stack)
        self.splitter.setSizes([260, 360, 520])

        root_layout.addWidget(self.query_container, stretch=1)

        self.empty_label = QLabel("선택된 세션이 없습니다")
        self.empty_label.setStyleSheet("font-size: 13px; color: #666; padding: 8px;")
        root_layout.addWidget(self.empty_label)

        self._configure_query_mode("segments")

    def _connect_live_events(self):
        if self._live_events_connected:
            logger.warning("[ResultView] live events already connected")
            return

        self.socket_service.analysis_session_status_changed.connect(
            self._on_analysis_session_status
        )
        self.socket_service.analysis_progress_ready.connect(
            self.live_monitor.handle_progress
        )
        self.socket_service.analysis_frame_result_ready.connect(
            self._on_analysis_frame_result
        )
        self.socket_service.analysis_track_confirmed_ready.connect(
            self._on_analysis_track_confirmed
        )
        self.socket_service.analysis_segment_saved.connect(
            self._on_analysis_segment_saved
        )
        self.socket_service.connected.connect(self._on_socket_connected)
        self.socket_service.disconnected.connect(self._on_socket_disconnected)
        self.socket_service.connection_state_changed.connect(
            self._on_socket_connection_state_changed
        )
        self.socket_service.error_occurred.connect(self._on_live_socket_error)
        self.live_monitor.analysis_sample_ready.connect(
            self.socket_service.send_analysis_sample
        )
        self._live_events_connected = True
        logger.info("[ResultView] live events connected once")

    def ensure_live_connection(self):
        self.socket_service.server_url = self.api_client.base_url
        return self.socket_service.ensure_connected()

    def set_input_source_type(self, source_type: str):
        self.current_input_source = source_type
        self.live_monitor.current_source_type = source_type
        self.is_query_panel_active = source_type != "WEBCAM"
        self._update_display_mode()

    def prepare_live_session(self, source_type: str):
        self.current_input_source = source_type
        self.current_session_id = None
        self.current_analysis_status = None
        self.has_received_segment_saved = False
        self._last_completed_session_id = None
        self.selected_session_source_type = None
        self.selected_session_payload = None
        self.loaded_segments = []
        self.loaded_tracks = []
        self.segment_sync_timer.stop()
        self.live_monitor.prepare_session(source_type)
        self.segment_detail_widget.clear_detail()
        self.track_detail_widget.clear_detail()
        self.is_query_panel_active = source_type != "WEBCAM"
        self._update_display_mode()
        if self.is_query_panel_active:
            self.load_sessions()

    def set_session_id(self, session_id: str):
        self.current_session_id = session_id
        self.live_monitor.set_session_id(session_id)
        self._select_session_row(session_id)

    def set_active_inspection_items(self, item_keys: list[str]):
        self.live_monitor.set_active_items(item_keys)

    def begin_shutdown(self):
        self._is_shutting_down = True
        self.pending_reload = False
        self.segment_sync_timer.stop()
        self.live_monitor.stop_local_camera()
        self._cleanup_workers()

    def load_sessions(self):
        if self._is_shutting_down or self._is_loading_sessions:
            return
        if self.session_list_worker and self.session_list_worker.isRunning():
            return

        self._is_loading_sessions = True
        worker = ApiWorker(self.api_client.get_sessions, 20)
        self.session_list_worker = worker
        worker.result_ready.connect(self._on_sessions_loaded)
        worker.error_occurred.connect(self._on_sessions_error)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(self._clear_session_list_worker)
        worker.start()

    def load_results(self, reason: str = "manual"):
        if self._is_shutting_down or self._is_loading_segments:
            return
        if self.segment_worker and self.segment_worker.isRunning():
            self.pending_reload = True
            return
        if not self.current_session_id:
            self.empty_label.setText("선택된 세션이 없습니다")
            return

        self._is_loading_segments = True
        if self.selected_session_source_type == "WEBCAM":
            worker = ApiWorker(self.api_client.get_session_tracks, self.current_session_id, 5)
            worker.result_ready.connect(self._on_tracks_loaded)
            worker.error_occurred.connect(self._on_tracks_error)
            self.current_query_kind = "tracks"
        else:
            timeout_sec = 15 if self._is_processing_video_session() else 5
            worker = ApiWorker(
                self.api_client.get_session_segments,
                self.current_session_id,
                timeout_sec,
            )
            worker.result_ready.connect(self._on_segments_loaded)
            worker.error_occurred.connect(self._on_segments_error)
            self.current_query_kind = "segments"

        self.segment_worker = worker
        self.list_worker = worker
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(self._clear_segment_worker)
        worker.start()
        logger.debug(
            "[ResultView] load_results reason=%s session_id=%s query_kind=%s",
            reason,
            self.current_session_id,
            self.current_query_kind,
        )

    def _reload_all(self):
        self.is_query_panel_active = True
        self._update_display_mode()
        self.load_sessions()
        if self.current_session_id:
            self.load_results(reason="manual_refresh")

    def _on_socket_connected(self):
        logger.info(
            "[ResultView] socket connected session_id=%s active_session=%s",
            self.current_session_id,
            self.socket_service.has_active_session(),
        )

    def _on_socket_disconnected(self):
        logger.warning(
            "[ResultView] socket disconnected session_id=%s current_status=%s",
            self.current_session_id,
            self.current_analysis_status,
        )
        if self.current_session_id and self.current_analysis_status not in {"completed", "failed"}:
            self.live_monitor.status_label.setText("연결 끊김, 재연결 대기 중")
            self.live_monitor._append_event("연결 끊김, 재연결 대기 중")

    def _on_socket_connection_state_changed(self, state: str):
        self._socket_connection_state = state
        logger.info(
            "[ResultView] socket connection state changed state=%s session_id=%s",
            state,
            self.current_session_id,
        )
        if state == "reconnected":
            self._recover_after_reconnect()

    def _recover_after_reconnect(self):
        if not self.current_session_id:
            self.load_sessions()
            return

        logger.info(
            "[ResultView] recovering session after reconnect session_id=%s",
            self.current_session_id,
        )
        self.live_monitor._append_event("재연결됨, 세션 상태 확인 중")
        self._refresh_current_session_state()
        self.load_sessions()
        self.load_results(reason="socket_reconnected")

    def _refresh_current_session_state(self):
        if not self.current_session_id:
            return

        try:
            session_payload = self.api_client.get_session(self.current_session_id, timeout_sec=5)
        except Exception as exc:
            logger.warning(
                "[ResultView] failed to refresh current session state session_id=%s error=%s",
                self.current_session_id,
                exc,
            )
            self.live_monitor._append_event(f"재연결 후 세션 조회 실패: {exc}")
            return

        self.selected_session_payload = session_payload
        self.selected_session_source_type = session_payload.get("source_type")
        status = session_payload.get("status")
        if status:
            self.current_analysis_status = status
            self.live_monitor.handle_session_status(
                {
                    "session_id": session_payload.get("session_id"),
                    "source_type": session_payload.get("source_type"),
                    "status": status,
                }
            )
            if status in {"completed", "failed", "stopped"}:
                self.segment_sync_timer.stop()

    def _on_sessions_loaded(self, payload: dict):
        self.loaded_sessions = payload.get("sessions", [])
        if self.current_session_id:
            matched_session = next(
                (
                    session
                    for session in self.loaded_sessions
                    if session.get("session_id") == self.current_session_id
                ),
                None,
            )
            if matched_session:
                self.selected_session_payload = matched_session
                self.selected_session_source_type = matched_session.get("source_type")
                matched_status = matched_session.get("status")
                if matched_status:
                    self.current_analysis_status = matched_status
        self._fill_session_table()
        if self.current_session_id:
            self._select_session_row(self.current_session_id)

    def _on_sessions_error(self, err_msg: str):
        self.empty_label.setText(f"세션 목록 조회 실패: {err_msg}")

    def _fill_session_table(self):
        self.session_table.setRowCount(len(self.loaded_sessions))
        for row_index, session in enumerate(self.loaded_sessions):
            display_session_no = session.get("session_no") or row_index + 1
            values = [
                str(display_session_no),
                session.get("source_type", "-"),
                session.get("status", "-"),
                str(session.get("created_at") or "-"),
            ]
            for col_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col_index == 0:
                    item.setData(Qt.UserRole, session.get("session_id"))
                self.session_table.setItem(row_index, col_index, item)

    def _on_session_cell_changed(self, current_row: int, _current_column: int, _previous_row: int, _previous_column: int):
        if current_row < 0:
            return

        self._activate_session_row(current_row)

    def _activate_session_row(self, row_index: int):
        session_item = self.session_table.item(row_index, 0)
        if session_item is None:
            return
        session_id = session_item.data(Qt.UserRole) or session_item.text()
        if not session_id:
            return
        if self.current_session_id == session_id and self.selected_session_payload is not None:
            return

        self.current_session_id = session_id
        self.live_monitor.set_session_id(session_id)
        self.selected_session_payload = next(
            (session for session in self.loaded_sessions if session.get("session_id") == session_id),
            None,
        )
        self.selected_session_source_type = (
            self.selected_session_payload.get("source_type")
            if self.selected_session_payload
            else None
        )
        self.is_query_panel_active = True
        self._configure_query_mode("tracks" if self.selected_session_source_type == "WEBCAM" else "segments")
        self.loaded_segments = []
        self.loaded_tracks = []
        self.segment_table.setRowCount(0)
        self.segment_detail_widget.clear_detail()
        self.track_detail_widget.clear_detail()
        self._update_display_mode()
        display_session_no = (
            self.selected_session_payload.get("session_no")
            if self.selected_session_payload
            else session_item.text()
        )
        self.empty_label.setText(f"선택된 세션: {display_session_no}")
        self.load_results(reason="session_selected")

    def _on_segments_loaded(self, payload: dict):
        self.loaded_segments = payload.get("segments", [])
        self.loaded_tracks = []
        self.current_query_kind = "segments"
        self._configure_query_mode("segments")
        self._fill_segment_table()
        self._select_first_result_if_needed()
        self.load_sessions()

    def _on_tracks_loaded(self, payload: dict):
        self.loaded_tracks = payload.get("tracks", [])
        self.loaded_segments = []
        self.current_query_kind = "tracks"
        self._configure_query_mode("tracks")
        self._fill_track_table()
        self._select_first_result_if_needed()
        self.load_sessions()

    def _on_segments_error(self, err_msg: str):
        self.empty_label.setText(f"세그먼트 조회 실패: {err_msg}")
        self.segment_detail_widget.clear_detail("세그먼트 정보를 불러오지 못했습니다")

    def _on_tracks_error(self, err_msg: str):
        self.empty_label.setText(f"추적 결과 조회 실패: {err_msg}")
        self.track_detail_widget.clear_detail("추적 결과를 불러오지 못했습니다")

    def _fill_segment_table(self):
        self.segment_table.setRowCount(len(self.loaded_segments))
        for row_index, segment in enumerate(self.loaded_segments):
            confirmed_violation_count = sum(
                1
                for person in segment.get("people", [])
                if self._is_confirmed_violation_person(person)
            )
            values = [
                str(segment.get("segment_index", "-")),
                f"{segment.get('segment_start_sec', 0)}s ~ {segment.get('segment_end_sec', 0)}s",
                str(segment.get("reference_time") or segment.get("created_at") or "-"),
                str(confirmed_violation_count),
                "Y" if confirmed_violation_count > 0 else "N",
            ]
            for col_index, value in enumerate(values):
                self.segment_table.setItem(row_index, col_index, QTableWidgetItem(value))

        if not self.loaded_segments:
            self.segment_detail_widget.clear_detail("선택된 세그먼트가 없습니다")

    def _fill_track_table(self):
        self.segment_table.setRowCount(len(self.loaded_tracks))
        for row_index, track in enumerate(self.loaded_tracks):
            values = [
                str(track.get("track_id", "-")),
                str(track.get("employee_no") or "-"),
                "Y" if track.get("ocr_confirmed") else "N",
                self._map_item_status(track.get("helmet_status")),
                self._map_item_status(track.get("vest_status")),
                self._map_track_status(track.get("overall_ppe_status")),
                str(track.get("violation_count") or 0),
                "Y" if track.get("representative_frame_path") else "N",
            ]
            for col_index, value in enumerate(values):
                self.segment_table.setItem(row_index, col_index, QTableWidgetItem(value))

        if not self.loaded_tracks:
            self.track_detail_widget.clear_detail("선택된 추적 결과가 없습니다")

    @staticmethod
    def _is_confirmed_violation_person(person: dict) -> bool:
        helmet_status = person.get("helmet_status") or "UNKNOWN"
        vest_status = person.get("vest_status") or "UNKNOWN"
        return bool(person.get("ocr_confirmed")) and (
            helmet_status == "NOT_WORN" or vest_status == "NOT_WORN"
        )

    @staticmethod
    def _map_track_status(value: str | None) -> str:
        mapping = {
            "COMPLIANT": "정상",
            "NON_COMPLIANT": "위반",
            "UNKNOWN": "미확인",
        }
        return mapping.get(str(value or "").upper(), "-")

    @staticmethod
    def _map_item_status(value: str | None) -> str:
        mapping = {
            "WORN": "착용",
            "WEARING": "착용",
            "NOT_WORN": "미착용",
            "NOT_WEARING": "미착용",
            "UNKNOWN": "확인불가",
        }
        return mapping.get(str(value or "").upper(), "-")

    def _select_first_result_if_needed(self):
        loaded_count = len(self.loaded_tracks) if self.current_query_kind == "tracks" else len(self.loaded_segments)
        if not loaded_count:
            self.empty_label.setText("조회 결과가 없습니다")
            return
        if self.segment_table.currentRow() < 0:
            self.segment_table.selectRow(0)
            self.segment_table.setCurrentCell(0, 0)
        if self.current_query_kind == "tracks":
            self.empty_label.setText(
                f"추적 결과 {len(self.loaded_tracks)}건 / 세션 {self.current_session_id}"
            )
        else:
            self.empty_label.setText(
                f"세그먼트 {len(self.loaded_segments)}건 / 세션 {self.current_session_id}"
            )

    def _on_result_item_selected(self):
        row = self.segment_table.currentRow()
        if self.current_query_kind == "tracks":
            if row < 0 or row >= len(self.loaded_tracks):
                self.track_detail_widget.clear_detail()
                return
            self.track_detail_widget.set_track_detail(self.loaded_tracks[row])
            return

        if row < 0 or row >= len(self.loaded_segments):
            self.segment_detail_widget.clear_detail()
            return
        self.segment_detail_widget.set_segment_detail(self.loaded_segments[row])

    def _sync_segments_fallback(self):
        if not self.has_received_segment_saved:
            return
        if self.current_session_id and not (self.segment_worker and self.segment_worker.isRunning()):
            self.load_results(reason="fallback")

    def _on_analysis_session_status(self, payload: dict):
        source_type = payload.get("source_type")
        session_id = payload.get("session_id")
        self.live_monitor.handle_session_status(payload)

        if not self.is_query_panel_active:
            self.current_input_source = source_type or self.current_input_source
            self._update_display_mode()

        if (
            not self.current_session_id
            and not self.is_query_panel_active
            and self.current_input_source == source_type
        ):
            self.set_session_id(session_id)

        status = payload.get("status")
        self.current_analysis_status = status
        if status == "completed" and self._last_completed_session_id == session_id:
            logger.info("[ResultView] duplicate completed ignored session_id=%s", session_id)
            return

        if (
            not self.is_query_panel_active
            and self.current_input_source == "WEBCAM"
            and status in {"started", "processing"}
        ):
            return

        if status in {"started", "processing"} and self.current_session_id == session_id:
            if self.has_received_segment_saved and not self.segment_sync_timer.isActive():
                self.segment_sync_timer.start()
        if status in {"completed", "failed", "stopping", "stopped"}:
            self.segment_sync_timer.stop()
        if status in {"completed", "failed", "stopped"} and self.current_session_id == session_id:
            if status == "completed":
                self._last_completed_session_id = session_id
            if self.current_input_source == "VIDEO_FILE" or self.is_query_panel_active:
                self.load_results(reason=f"session_status:{status}")
            else:
                self.load_sessions()

    def _on_analysis_segment_saved(self, payload: dict):
        if self.current_input_source == "WEBCAM" and not self.is_query_panel_active:
            return

        self.live_monitor.handle_segment_saved(payload)
        if payload.get("session_id") != self.current_session_id:
            return

        self.has_received_segment_saved = True
        if self.is_query_panel_active:
            if (
                self.current_analysis_status in {"started", "processing"}
                and not self.segment_sync_timer.isActive()
            ):
                self.segment_sync_timer.start()
            self.load_results(reason="segment_saved")

    def _on_analysis_frame_result(self, payload: dict):
        logger.info(
            "[ResultView] analysis_frame_result received session_id=%s frame_no=%s payload_keys=%s tracks_count=%s detections_count=%s",
            payload.get("session_id"),
            payload.get("frame_no"),
            sorted(list(payload.keys())),
            payload.get("tracks_count", 0),
            len(payload.get("detections", [])),
        )
        self.live_monitor.handle_frame_result(payload)
        logger.info(
            "[ResultView] analysis_frame_result forwarded session_id=%s frame_no=%s target=%s",
            payload.get("session_id"),
            payload.get("frame_no"),
            "AnalysisLiveMonitorWidget.handle_frame_result",
        )

    def _on_analysis_track_confirmed(self, payload: dict):
        self.live_monitor.handle_track_confirmed(payload)

    def _on_live_socket_error(self, err_msg: str):
        self.live_monitor.handle_session_status(
            {
                "session_id": self.current_session_id,
                "source_type": self.current_input_source,
                "status": "failed",
            }
        )
        self.segment_sync_timer.stop()
        self.live_monitor._append_event(f"소켓 오류: {err_msg}")

    def _clear_session_list_worker(self):
        self._is_loading_sessions = False
        self.session_list_worker = None

    def _clear_segment_worker(self):
        self._is_loading_segments = False
        self.segment_worker = None
        self.list_worker = None
        if self.pending_reload and not self._is_shutting_down:
            self.pending_reload = False
            self.load_results(reason="pending_reload")
            return
        self.pending_reload = False

    def _select_session_row(self, session_id: str):
        for row_index in range(self.session_table.rowCount()):
            item = self.session_table.item(row_index, 0)
            if item and (item.data(Qt.UserRole) == session_id or item.text() == session_id):
                self.session_table.selectRow(row_index)
                self.session_table.setCurrentCell(row_index, 0)
                return

    def _is_processing_video_session(self) -> bool:
        return (
            self.current_input_source == "VIDEO_FILE"
            and self.current_analysis_status in {"started", "processing"}
        )

    def _is_live_analysis_mode(self) -> bool:
        return self.current_input_source == "WEBCAM" and not self.is_query_panel_active

    def _update_display_mode(self):
        is_live_mode = self._is_live_analysis_mode()
        self.live_container.setVisible(is_live_mode)
        self.query_container.setVisible(not is_live_mode)

        if is_live_mode:
            self.live_monitor.start_local_camera()
            self.empty_label.setText("웹캠 실시간 분석 화면입니다")
            self.empty_label.setVisible(False)
            self.live_monitor.current_source_type = "WEBCAM"
            self.live_monitor.update_live_ui_visibility(
                "WEBCAM",
                self.current_analysis_status,
            )
        else:
            self.live_monitor.stop_local_camera()
            self.empty_label.setVisible(True)
            self.live_monitor.update_live_ui_visibility(
                self.current_input_source,
                self.current_analysis_status,
            )
            self.load_sessions()

    def _configure_query_mode(self, mode: str):
        self.current_query_kind = mode
        if mode == "tracks":
            self.item_list_label.setText("추적 결과 목록")
            self.segment_table.setColumnCount(8)
            self.segment_table.setHorizontalHeaderLabels(
                ["Track ID", "직원번호", "OCR 확정", "헬멧 상태", "조끼 상태", "최종 상태", "위반 횟수", "대표 프레임"]
            )
            self.detail_stack.setCurrentWidget(self.track_detail_widget)
        else:
            self.item_list_label.setText("세그먼트 목록")
            self.segment_table.setColumnCount(5)
            self.segment_table.setHorizontalHeaderLabels(
                ["세그먼트", "시간", "기준 시각", "OCR 확정 위반 인원", "위반 여부"]
            )
            self.detail_stack.setCurrentWidget(self.segment_detail_widget)

    def _cleanup_workers(self):
        for worker_attr in ("session_list_worker", "segment_worker"):
            worker = getattr(self, worker_attr, None)
            if worker and worker.isRunning():
                worker.requestInterruption()
                worker.quit()
                worker.wait(3000)

    def closeEvent(self, event):
        self.begin_shutdown()
        super().closeEvent(event)
