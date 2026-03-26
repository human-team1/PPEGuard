import base64
import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QListWidget,
    QProgressBar,
    QVBoxLayout,
)

from app.config.result_dashboard_config import LIVE_MONITOR_CARD_DEFINITIONS
from app.models.dashboard_models import calculate_live_monitor_kpis, get_latest_segment
from app.ui.widgets.dashboard_metric_card import DashboardMetricCard


logger = logging.getLogger(__name__)


class AnalysisLiveMonitorWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_session_id = None
        self.current_source_type = None
        self.latest_detections = []
        self.active_items = {"helmet", "vest"}
        self.total_segments = 0
        self.latest_segment_payload = None
        self._init_ui()

    def _init_ui(self):
        self.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        title = QLabel("실시간 진행 현황")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        self.status_label = QLabel("대기 중")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_text_label = QLabel("0%")
        self.time_label = QLabel("00:00 / 00:00")
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_text_label)
        layout.addWidget(self.time_label)

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

        self.preview_label = QLabel("실시간 프레임 미리보기가 없습니다")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(240)
        self.preview_label.setStyleSheet(
            "background-color: black; color: white; border: 1px solid #999;"
        )
        layout.addWidget(self.preview_label)

        self.event_list = QListWidget()
        self.event_list.setMaximumHeight(120)
        layout.addWidget(self.event_list)

    def prepare_session(self, source_type: str):
        self.current_session_id = None
        self.current_source_type = source_type
        self.latest_detections = []
        self.total_segments = 0
        self.latest_segment_payload = None
        self.status_label.setText(f"{source_type} 세션 준비 중")
        self.progress_bar.setValue(0)
        self.progress_text_label.setText("0%")
        self.time_label.setText("00:00 / 00:00")
        self._update_kpi_cards()
        self.preview_label.clear()
        self.preview_label.setText("실시간 프레임 미리보기가 없습니다")
        self.event_list.clear()

        is_webcam = source_type == "WEBCAM"
        self.progress_bar.setVisible(not is_webcam)
        self.progress_text_label.setVisible(not is_webcam)
        self.time_label.setVisible(not is_webcam)

    def set_session_id(self, session_id: str | None):
        self.current_session_id = session_id

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

        self.status_label.setText(f"{source_type} 세션 상태: {status}")
        if status in {"completed", "failed", "stopping"}:
            self.latest_detections = []
            if status != "processing":
                self.preview_label.clear()
                self.preview_label.setText("실시간 프레임 미리보기가 없습니다")
        self._append_event(f"세션 상태 변경: {status}")

    def handle_progress(self, payload: dict):
        if not self._matches(payload):
            return

        current_time_sec = float(payload.get("current_time_sec") or 0.0)
        total_time_sec = float(payload.get("total_time_sec") or 0.0)
        progress_percent = int(payload.get("progress_percent") or 0)

        if self.current_source_type != "WEBCAM":
            self.progress_bar.setValue(progress_percent)
            self.progress_text_label.setText(f"{progress_percent}%")
            self.time_label.setText(
                f"{self._format_time(current_time_sec)} / {self._format_time(total_time_sec)}"
            )

    def handle_frame_result(self, payload: dict):
        if not self._matches(payload):
            return

        self.latest_detections = payload.get("detections", [])
        preview_frame = payload.get("preview_frame")
        if not preview_frame:
            self.preview_label.clear()
            self.preview_label.setText("실시간 프레임 미리보기가 없습니다")
            return

        try:
            image_bytes = base64.b64decode(preview_frame)
            image = QImage.fromData(image_bytes, "JPG")
        except Exception:
            image = QImage()

        if image.isNull():
            self.preview_label.clear()
            self.preview_label.setText("프레임 디코딩에 실패했습니다")
            return

        pixmap = QPixmap.fromImage(image)
        draw_pixmap = pixmap.copy()
        painter = QPainter(draw_pixmap)
        for detection in self.latest_detections:
            bbox = detection.get("bbox", {})
            x1 = int(bbox.get("x1", 0))
            y1 = int(bbox.get("y1", 0))
            x2 = int(bbox.get("x2", 0))
            y2 = int(bbox.get("y2", 0))
            label = (
                f"P:{detection.get('local_person_id', detection.get('track_id'))} "
                f"E:{detection.get('employee_id') or '-'} "
                f"O:{detection.get('ocr_number') or '-'} "
                f"H:{detection.get('helmet_status')} "
                f"V:{detection.get('vest_status')}"
            )

            pen_color = QColor(255, 0, 0)
            if (
                detection.get("helmet_status") == "WORN"
                and detection.get("vest_status") == "WORN"
            ):
                pen_color = QColor(57, 255, 20)

            painter.setPen(QPen(pen_color, 2))
            painter.drawRect(x1, y1, max(x2 - x1, 1), max(y2 - y1, 1))
            painter.drawText(x1, y1 - 4 if y1 > 16 else y1 + 14, label)
        painter.end()

        self.preview_label.setPixmap(
            draw_pixmap.scaled(
                self.preview_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

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
        latest_segment = get_latest_segment(segments)
        self.total_segments = len(segments)
        self.latest_segment_payload = latest_segment
        self._update_kpi_cards()

    def _update_kpi_cards(self):
        values = calculate_live_monitor_kpis(
            latest_segment=self.latest_segment_payload,
            total_segments=self.total_segments,
            active_items=list(self.active_items),
        )
        logger.debug("[LiveMonitor] kpi updated total_segments=%s", self.total_segments)
        for key, card in self.kpi_cards.items():
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

    @staticmethod
    def _format_time(seconds: float) -> str:
        total_seconds = int(seconds or 0)
        minutes = total_seconds // 60
        remain_seconds = total_seconds % 60
        return f"{minutes:02d}:{remain_seconds:02d}"
