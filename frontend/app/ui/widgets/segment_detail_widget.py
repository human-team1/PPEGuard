from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class SegmentDetailWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.title_label = QLabel("세그먼트 상세")
        self.title_label.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(self.title_label)

        self.best_frame_label = QLabel("선택된 세그먼트가 없습니다")
        self.best_frame_label.setAlignment(Qt.AlignCenter)
        self.best_frame_label.setMinimumHeight(280)
        self.best_frame_label.setStyleSheet(
            "background-color: #f3f3f3; color: #666; border: 1px solid #ccc;"
        )
        layout.addWidget(self.best_frame_label)

        self.meta_layout = QFormLayout()
        self.lbl_segment = QLabel("-")
        self.lbl_time_range = QLabel("-")
        self.lbl_reference_time = QLabel("-")
        self.lbl_confirmed_count = QLabel("-")
        self.lbl_frame_path = QLabel("-")
        self.lbl_frame_path.setWordWrap(True)
        self.meta_layout.addRow("세그먼트:", self.lbl_segment)
        self.meta_layout.addRow("시간 범위:", self.lbl_time_range)
        self.meta_layout.addRow("분석 시각:", self.lbl_reference_time)
        self.meta_layout.addRow("OCR 확정 위반 인원:", self.lbl_confirmed_count)
        self.meta_layout.addRow("베스트 프레임 경로:", self.lbl_frame_path)
        layout.addLayout(self.meta_layout)

        self.people_table = QTableWidget(self)
        self.people_table.setColumnCount(8)
        self.people_table.setHorizontalHeaderLabels(
            [
                "직원번호",
                "OCR 확정",
                "위반유형",
                "x1",
                "y1",
                "x2",
                "y2",
                "track_id",
            ]
        )
        layout.addWidget(self.people_table)

    def clear_detail(self, message: str = "선택된 세그먼트가 없습니다"):
        self.title_label.setText("세그먼트 상세")
        self.best_frame_label.clear()
        self.best_frame_label.setText(message)
        self.lbl_segment.setText("-")
        self.lbl_time_range.setText("-")
        self.lbl_reference_time.setText("-")
        self.lbl_confirmed_count.setText("-")
        self.lbl_frame_path.setText("-")
        self.people_table.setRowCount(0)

    def set_segment_detail(self, segment: dict):
        if not segment:
            self.clear_detail()
            return

        segment_index = int(segment.get("segment_index") or 0)
        segment_id = segment.get("segment_id") or "-"
        people = segment.get("people", [])
        confirmed_people = [person for person in people if self._is_confirmed_violation(person)]

        self.title_label.setText(f"세그먼트 상세 [{segment_index}]")
        self.lbl_segment.setText(f"ID {segment_id} / 순번 {segment_index}")
        self.lbl_time_range.setText(
            f"{segment.get('segment_start_sec', 0)}s ~ {segment.get('segment_end_sec', 0)}s"
        )
        self.lbl_reference_time.setText(
            str(segment.get("reference_time") or segment.get("created_at") or "-")
        )
        self.lbl_confirmed_count.setText(str(len(confirmed_people)))
        frame_path = segment.get("representative_frame_path") or "-"
        self.lbl_frame_path.setText(str(frame_path))
        self._set_best_frame(frame_path)
        self._fill_people_table(confirmed_people)

    def _set_best_frame(self, frame_path: str):
        self.best_frame_label.clear()
        resolved_path = self._resolve_frame_path(frame_path)
        if not resolved_path:
            self.best_frame_label.setText("베스트 프레임이 없습니다")
            return

        pixmap = QPixmap(resolved_path)
        if pixmap.isNull():
            self.best_frame_label.setText("베스트 프레임을 불러올 수 없습니다")
            return

        self.best_frame_label.setPixmap(
            pixmap.scaled(
                self.best_frame_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    def _fill_people_table(self, people: list[dict]):
        self.people_table.setRowCount(len(people))
        for row_index, person in enumerate(people):
            bbox = self._bbox(person)
            values = [
                person.get("employee_id") or person.get("ocr_number") or "-",
                "Y" if person.get("ocr_confirmed") else "N",
                self._violation_type(person),
                str(bbox.get("x1", "-")),
                str(bbox.get("y1", "-")),
                str(bbox.get("x2", "-")),
                str(bbox.get("y2", "-")),
                str(person.get("track_id") or "-"),
            ]
            for col_index, value in enumerate(values):
                self.people_table.setItem(row_index, col_index, QTableWidgetItem(value))

    @staticmethod
    def _bbox(person: dict) -> dict:
        if person.get("bbox"):
            return person["bbox"]
        return {
            "x1": person.get("bbox_x1"),
            "y1": person.get("bbox_y1"),
            "x2": person.get("bbox_x2"),
            "y2": person.get("bbox_y2"),
        }

    @staticmethod
    def _violation_type(person: dict) -> str:
        violations = []
        if SegmentDetailWidget._segment_status(person, "helmet_status") == "NOT_WORN":
            violations.append("헬멧 미착용")
        if SegmentDetailWidget._segment_status(person, "vest_status") == "NOT_WORN":
            violations.append("조끼 미착용")
        return ", ".join(violations) if violations else "정상"

    @classmethod
    def _is_confirmed_violation(cls, person: dict) -> bool:
        return bool(person.get("ocr_confirmed")) and cls._violation_type(person) != "정상"

    @staticmethod
    def _segment_status(person: dict, field_name: str) -> str:
        return person.get(field_name) or "UNKNOWN"

    @staticmethod
    def _resolve_frame_path(frame_path: str) -> str | None:
        if not frame_path or frame_path == "-":
            return None
        candidates = [frame_path]
        if not os.path.isabs(frame_path):
            candidates.append(os.path.join(os.getcwd(), frame_path))
            candidates.append(os.path.join(os.getcwd(), "..", "backend", frame_path))
        for candidate in candidates:
            normalized = os.path.normpath(candidate)
            if os.path.exists(normalized):
                return normalized
        return None
