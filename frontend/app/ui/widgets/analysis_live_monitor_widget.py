import logging

from PySide6.QtCore import QSize, Qt, Signal, Slot
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QListWidget, QProgressBar, QSizePolicy, QVBoxLayout

from app.config.result_dashboard_config import LIVE_MONITOR_CARD_DEFINITIONS
from app.models.dashboard_models import calculate_live_monitor_kpis, get_latest_segment
from app.services.webcam_service import WebcamService
from app.ui.widgets.dashboard_metric_card import DashboardMetricCard


logger = logging.getLogger(__name__)


class StablePreviewLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._source_pixmap = QPixmap()
        self._base_size = QSize(640, 360)
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setMinimumSize(320, 180)
        self.setStyleSheet(
            "background-color: black; color: white; border: 1px solid #999;"
        )

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return max(180, int(width * 9 / 16))

    def sizeHint(self) -> QSize:
        return QSize(self._base_size)

    def minimumSizeHint(self) -> QSize:
        return QSize(320, 180)

    def set_frame_pixmap(self, pixmap: QPixmap):
        self._source_pixmap = pixmap
        super().clear()
        self._render_scaled_pixmap()

    def show_placeholder(self, text: str):
        self._source_pixmap = QPixmap()
        super().clear()
        super().setText(text)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._source_pixmap.isNull():
            self._render_scaled_pixmap()

    def _render_scaled_pixmap(self):
        if self._source_pixmap.isNull():
            return
        target_size = self.contentsRect().size()
        if target_size.width() <= 0 or target_size.height() <= 0:
            return
        scaled = self._source_pixmap.scaled(
            target_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        super().setPixmap(scaled)


class AnalysisLiveMonitorWidget(QFrame):
    analysis_sample_ready = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_session_id = None
        self.current_source_type = "VIDEO_FILE"
        self.current_session_state = "idle"
        self.webcam_service = None
        self.latest_detections = []
        self.latest_local_frame = QImage()
        self.latest_result_frame_no = -1
        self.latest_result_frame_width = 640
        self.latest_result_frame_height = 480
        self.latest_processed_frames = 0
        self.live_active_person_count = 0
        self.live_violating_person_count = 0
        self.live_violation_rate = 0.0
        self.active_items = {"helmet", "vest"}
        self.total_segments = 0
        self.latest_segment_payload = None
        self._last_history_snapshot = None
        self.preview_mirrored = False
        self._init_ui()

    def _init_ui(self):
        self.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        title = QLabel("실시간 진행 현황")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        self.helper_label = QLabel("웹캠 분석을 시작하면 실시간 결과가 표시됩니다")
        self.helper_label.setStyleSheet("font-size: 12px; color: #546E7A;")
        self.helper_label.setWordWrap(True)
        layout.addWidget(self.helper_label)

        self.progress_container = QFrame(self)
        progress_layout = QVBoxLayout(self.progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(4)

        self.status_label = QLabel("대기 중")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_text_label = QLabel("0%")
        self.time_label = QLabel("00:00 / 00:00")
        progress_layout.addWidget(self.status_label)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_text_label)
        progress_layout.addWidget(self.time_label)
        layout.addWidget(self.progress_container)

        self.kpi_container = QFrame(self)
        self.kpi_layout = QGridLayout(self.kpi_container)
        self.kpi_layout.setContentsMargins(0, 0, 0, 0)
        self.kpi_cards = {}
        for index, card_meta in enumerate(LIVE_MONITOR_CARD_DEFINITIONS):
            card = DashboardMetricCard(
                card_meta["label"],
                "0",
                card_meta["accent"],
                parent=self.kpi_container,
            )
            self.kpi_cards[card_meta["key"]] = card
            self.kpi_layout.addWidget(card, index // 2, index % 2)
        layout.addWidget(self.kpi_container)

        self.preview_container = QFrame(self)
        preview_layout = QVBoxLayout(self.preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        self.preview_label = StablePreviewLabel(self.preview_container)
        self.preview_label.show_placeholder("실시간 프레임 미리보기가 없습니다")
        preview_layout.addWidget(self.preview_label)
        layout.addWidget(self.preview_container)

        self.event_list = QListWidget()
        self.event_list.setMaximumHeight(120)
        layout.addWidget(self.event_list)
        self.update_live_ui_visibility(self.current_source_type, self.current_session_state)
        self._update_kpi_cards()

    def prepare_session(self, source_type: str):
        self.current_session_id = None
        self.current_source_type = source_type
        self.current_session_state = "idle"
        self.latest_detections = []
        self.latest_local_frame = QImage()
        self.latest_result_frame_no = -1
        self.latest_result_frame_width = 640
        self.latest_result_frame_height = 480
        self.latest_processed_frames = 0
        self.live_active_person_count = 0
        self.live_violating_person_count = 0
        self.live_violation_rate = 0.0
        self.total_segments = 0
        self.latest_segment_payload = None
        self._last_history_snapshot = None
        self.status_label.setText(f"{source_type} 세션 준비 중")
        self.progress_bar.setValue(0)
        self.progress_text_label.setText("0%")
        self.time_label.setText("00:00 / 00:00")
        self._update_kpi_cards()
        self._reset_preview()
        self.event_list.clear()
        self.update_live_ui_visibility(source_type, self.current_session_state)

    def set_session_id(self, session_id: str | None):
        self.current_session_id = session_id

    def start_local_camera(self, camera_id: int = 0):
        if self.webcam_service and self.webcam_service.isRunning():
            return

        self.stop_local_camera()
        self.webcam_service = WebcamService(camera_id, self, fps_limit=3)
        self.webcam_service.frame_ready.connect(self.update_local_preview_frame)
        self.webcam_service.raw_frame_ready.connect(self.analysis_sample_ready.emit)
        self.webcam_service.error_occurred.connect(self._handle_camera_error)
        self.webcam_service.finished.connect(self._clear_webcam_service)
        self.webcam_service.stopped.connect(self._clear_webcam_service)
        self.webcam_service.start()

    def stop_local_camera(self):
        webcam_service = self.webcam_service
        if webcam_service:
            if webcam_service.isRunning():
                webcam_service.stop()
            self._clear_webcam_service()
        self.latest_local_frame = QImage()
        self.latest_detections = []
        self.latest_result_frame_no = -1
        self.latest_result_frame_height = 480
        self._last_history_snapshot = None
        self.preview_label.show_placeholder("웹캠 분석을 시작하면 실시간 프레임이 표시됩니다")

    def set_active_items(self, item_keys: list[str]):
        self.active_items = set(item_keys)
        self._update_kpi_cards()

    def handle_session_status(self, payload: dict):
        source_type = payload.get("source_type")
        session_id = payload.get("session_id")
        status = payload.get("status", "unknown")

        if self.current_session_id and session_id != self.current_session_id:
            return
        if not self.current_session_id and self.current_source_type == source_type:
            self.current_session_id = session_id

        self.current_session_state = status
        self.status_label.setText(f"{source_type} 세션 상태: {status}")
        if status in {"completed", "failed", "stopping"}:
            self.latest_detections = []
            if self.current_source_type == "WEBCAM" and status != "processing":
                self._reset_preview()
        self.update_live_ui_visibility(source_type, status)
        self._append_event(f"세션 상태 변경: {status}")

    def handle_progress(self, payload: dict):
        if not self._matches(payload):
            return

        current_time_sec = float(payload.get("current_time_sec") or 0.0)
        total_time_sec = float(payload.get("total_time_sec") or 0.0)
        progress_percent = int(payload.get("progress_percent") or 0)
        self.latest_processed_frames = int(payload.get("processed_frames") or 0)
        self.live_active_person_count = int(
            payload.get("active_person_count")
            or payload.get("current_counts", {}).get("active_track_count")
            or 0
        )
        self.live_violating_person_count = int(
            payload.get("violating_person_count")
            or payload.get("current_counts", {}).get("violating_person_count")
            or 0
        )
        self.live_violation_rate = float(payload.get("violation_rate") or 0.0)
        current_counts = payload.get("current_counts") or {}
        active_tracks = self.live_active_person_count
        violations_count = self.live_violating_person_count
        history_snapshot = (
            self.latest_processed_frames,
            active_tracks,
            violations_count,
        )

        if self.current_source_type != "WEBCAM":
            self.progress_bar.setValue(progress_percent)
            self.progress_text_label.setText(f"{progress_percent}%")
            self.time_label.setText(
                f"{self._format_time(current_time_sec)} / {self._format_time(total_time_sec)}"
            )
        elif history_snapshot != self._last_history_snapshot:
            self._append_event(
                f"프레임 {self.latest_processed_frames} 처리 / 활성 track {active_tracks} / 위반 {violations_count}"
            )
            self._last_history_snapshot = history_snapshot
        self._update_kpi_cards()

    def handle_frame_result(self, payload: dict):
        if not self._matches(payload):
            return
        if self.current_source_type != "WEBCAM":
            return

        frame_no = int(payload.get("frame_no") or -1)
        if frame_no >= 0 and frame_no < self.latest_result_frame_no:
            logger.warning(
                "[LiveMonitor] stale frame_result ignored session_id=%s frame_no=%s latest_frame_no=%s",
                payload.get("session_id"),
                frame_no,
                self.latest_result_frame_no,
            )
            return

        if frame_no >= 0:
            self.latest_result_frame_no = frame_no
        self.latest_detections = payload.get("detections", [])
        self.latest_result_frame_width = int(payload.get("frame_width") or 640)
        self.latest_result_frame_height = int(payload.get("frame_height") or 480)
        logger.info(
            "[LiveMonitor] frame_result update session_id=%s frame_no=%s detections_count=%s render=%s",
            payload.get("session_id"),
            frame_no,
            len(self.latest_detections),
            "_render_overlay_preview",
        )
        self._render_overlay_preview()

    def handle_track_confirmed(self, payload: dict):
        if not self._matches(payload):
            return
        self._append_event(
            f"OCR 확정 track {payload.get('track_id')} / {payload.get('employee_id') or '-'}"
        )

    @Slot(QImage)
    def update_local_preview_frame(self, image: QImage):
        if image.isNull():
            return

        self.latest_local_frame = image.copy()
        self._render_overlay_preview()

    def _render_overlay_preview(self):
        if self.latest_local_frame.isNull():
            return

        draw_image = self.latest_local_frame.copy()
        painter = QPainter(draw_image)
        scale_x = max(draw_image.width(), 1) / float(max(self.latest_result_frame_width, 1))
        scale_y = max(draw_image.height(), 1) / float(max(self.latest_result_frame_height, 1))
        for index, detection in enumerate(self.latest_detections):
            bbox = detection.get("bbox", {})
            raw_x1 = int(bbox.get("x1", 0))
            raw_y1 = int(bbox.get("y1", 0))
            raw_x2 = int(bbox.get("x2", 0))
            raw_y2 = int(bbox.get("y2", 0))
            x1 = int(raw_x1 * scale_x)
            y1 = int(raw_y1 * scale_y)
            x2 = int(raw_x2 * scale_x)
            y2 = int(raw_y2 * scale_y)
            if self.preview_mirrored:
                mirrored_x1 = draw_image.width() - x2
                mirrored_x2 = draw_image.width() - x1
                x1, x2 = mirrored_x1, mirrored_x2

            label_parts = []
            if detection.get("employee_no") or detection.get("employee_id"):
                label_parts.append(str(detection.get("employee_no") or detection.get("employee_id")))
            if detection.get("track_id") is not None:
                label_parts.append(f"track {detection.get('track_id')}")
            if detection.get("violation_type") and detection.get("violation_type") != "normal":
                label_parts.append(str(detection.get("violation_type")))
            else:
                if detection.get("helmet_status") == "NOT_WORN":
                    label_parts.append("helmet_missing")
                if detection.get("vest_status") == "NOT_WORN":
                    label_parts.append("vest_missing")
            if detection.get("ocr_confirmed"):
                label_parts.append("ocr")
            label = " / ".join(label_parts) if label_parts else "track -"

            pen_color = QColor(255, 0, 0)
            if (
                detection.get("helmet_status") == "WORN"
                and detection.get("vest_status") == "WORN"
            ):
                pen_color = QColor(57, 255, 20)

            painter.setPen(QPen(pen_color, 2))
            painter.drawRect(x1, y1, max(x2 - x1, 1), max(y2 - y1, 1))
            painter.drawText(x1, y1 - 4 if y1 > 16 else y1 + 14, label)
            if index == 0:
                logger.info(
                    "[LiveMonitor] overlay sample session_id=%s frame_no=%s raw_bbox=(%s,%s,%s,%s) scaled_bbox=(%s,%s,%s,%s) frame_size=%sx%s preview_size=%sx%s mirrored=%s",
                    self.current_session_id,
                    self.latest_result_frame_no,
                    raw_x1,
                    raw_y1,
                    raw_x2,
                    raw_y2,
                    x1,
                    y1,
                    x2,
                    y2,
                    self.latest_result_frame_width,
                    self.latest_result_frame_height,
                    draw_image.width(),
                    draw_image.height(),
                    self.preview_mirrored,
                )
        painter.end()

        self.preview_label.set_frame_pixmap(QPixmap.fromImage(draw_image))

    def handle_segment_saved(self, payload: dict):
        if not self._matches(payload):
            return
        self.total_segments = max(self.total_segments, int(payload.get("segment_index") or 0) + 1)
        self.latest_segment_payload = {"people": payload.get("person_results", [])}
        self._update_kpi_cards()
        self._append_event(
            "세그먼트 저장 완료: "
            f"{payload.get('segment_index')} "
            f"({payload.get('segment_start_sec')}~{payload.get('segment_end_sec')}초)"
        )

    def sync_from_segments_response(self, payload: dict):
        segments = payload.get("segments", [])
        self.total_segments = len(segments)
        self.latest_segment_payload = get_latest_segment(segments)
        self._update_kpi_cards()

    def _update_kpi_cards(self):
        if self.current_source_type == "WEBCAM":
            webcam_values = {
                "current_people": str(self.live_active_person_count),
                "current_violations": str(self.live_violating_person_count),
                "current_violation_rate": (
                    f"{self.live_violation_rate:.1f}%"
                    if self.live_violation_rate % 1
                    else f"{int(self.live_violation_rate)}%"
                ),
                "total_segments": str(self.latest_processed_frames),
            }
            for key, card in self.kpi_cards.items():
                if key == "total_segments":
                    card.title_label.setText("처리 프레임 수")
                card.set_value(webcam_values.get(key, "0"))
            return

        values = calculate_live_monitor_kpis(
            latest_segment=self.latest_segment_payload,
            total_segments=self.total_segments,
            active_items=list(self.active_items),
        )
        for key, card in self.kpi_cards.items():
            if key == "total_segments" and self.current_source_type == "WEBCAM":
                card.title_label.setText("처리 프레임 수")
                card.set_value(str(self.latest_processed_frames))
                continue
            if key == "total_segments":
                card.title_label.setText("총 세그먼트 수")
            card.set_value(values.get(key, "0"))

    def _matches(self, payload: dict) -> bool:
        session_id = payload.get("session_id")
        source_type = payload.get("source_type", self.current_source_type)
        if self.current_session_id:
            return session_id == self.current_session_id
        return self.current_source_type == source_type

    def _append_event(self, text: str):
        self.event_list.insertItem(0, text)
        while self.event_list.count() > 20:
            self.event_list.takeItem(self.event_list.count() - 1)

    def update_preview_visibility(self, source_type: str | None):
        normalized = (source_type or "").strip().upper()
        is_webcam = normalized == "WEBCAM"
        logger.info(
            "[LiveMonitor] update_preview_visibility source_type=%s normalized=%s is_webcam=%s",
            source_type,
            normalized,
            is_webcam,
        )
        self.preview_container.setVisible(is_webcam)

    def update_live_ui_visibility(
        self,
        source_type: str | None = None,
        session_state: str | None = None,
    ):
        normalized_source = (source_type or self.current_source_type or "").strip().upper()
        normalized_state = (session_state or self.current_session_state or "idle").strip().lower()

        self.current_source_type = normalized_source or self.current_source_type
        self.current_session_state = normalized_state

        is_webcam = normalized_source == "WEBCAM"
        is_video = normalized_source == "VIDEO_FILE"
        is_webcam_running = is_webcam and normalized_state in {"started", "processing"}
        is_webcam_prestart = is_webcam and normalized_state in {"idle", "ready", "unknown", ""}

        self.progress_container.setVisible(is_video)
        self.helper_label.setVisible(is_webcam_prestart)
        self.status_label.setVisible(is_video)

        if is_video:
            self.progress_bar.setVisible(True)
            self.progress_text_label.setVisible(True)
            self.time_label.setVisible(True)
        else:
            self.progress_bar.setVisible(False)
            self.progress_text_label.setVisible(False)
            self.time_label.setVisible(False)

        self.preview_container.setVisible(is_webcam)
        self.kpi_container.setVisible(is_webcam or is_video)

        if is_webcam_prestart:
            if self.latest_local_frame.isNull():
                self.preview_label.show_placeholder("웹캠 분석을 시작하면 실시간 프레임이 표시됩니다")
        elif is_webcam_running and self.preview_label.pixmap() is None:
            self.preview_label.show_placeholder("실시간 프레임 미리보기가 없습니다")

        logger.info(
            "[LiveMonitor] update_live_ui_visibility source_type=%s session_state=%s video=%s webcam=%s webcam_running=%s",
            normalized_source,
            normalized_state,
            is_video,
            is_webcam,
            is_webcam_running,
        )

    def _reset_preview(self):
        self.preview_label.show_placeholder("실시간 프레임 미리보기가 없습니다")

    def _handle_camera_error(self, err_msg: str):
        self.preview_label.show_placeholder(f"웹캠 오류: {err_msg}")
        self._append_event(f"웹캠 오류: {err_msg}")

    def _clear_webcam_service(self):
        self.webcam_service = None

    @staticmethod
    def _format_time(seconds: float) -> str:
        total_seconds = int(seconds or 0)
        minutes = total_seconds // 60
        remain_seconds = total_seconds % 60
        return f"{minutes:02d}:{remain_seconds:02d}"
