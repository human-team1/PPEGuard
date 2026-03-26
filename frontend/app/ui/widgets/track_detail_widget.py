from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFormLayout, QFrame, QLabel, QVBoxLayout


class TrackDetailWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.title_label = QLabel("추적 결과 상세")
        self.title_label.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(self.title_label)

        self.image_label = QLabel("선택된 추적 결과가 없습니다")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumHeight(280)
        self.image_label.setStyleSheet(
            "background-color: #f3f3f3; color: #666; border: 1px solid #ccc;"
        )
        layout.addWidget(self.image_label)

        self.meta_layout = QFormLayout()
        self.lbl_track_id = QLabel("-")
        self.lbl_employee_no = QLabel("-")
        self.lbl_ocr_confirmed = QLabel("-")
        self.lbl_ocr_text = QLabel("-")
        self.lbl_ocr_confidence = QLabel("-")
        self.lbl_overall = QLabel("-")
        self.lbl_helmet = QLabel("-")
        self.lbl_vest = QLabel("-")
        self.lbl_violation_count = QLabel("-")
        self.lbl_first_seen = QLabel("-")
        self.lbl_last_seen = QLabel("-")
        self.lbl_frame_path = QLabel("-")
        self.lbl_frame_path.setWordWrap(True)

        self.meta_layout.addRow("Track ID:", self.lbl_track_id)
        self.meta_layout.addRow("직원번호:", self.lbl_employee_no)
        self.meta_layout.addRow("OCR 확정:", self.lbl_ocr_confirmed)
        self.meta_layout.addRow("OCR 원문:", self.lbl_ocr_text)
        self.meta_layout.addRow("OCR 신뢰도:", self.lbl_ocr_confidence)
        self.meta_layout.addRow("최종 PPE 상태:", self.lbl_overall)
        self.meta_layout.addRow("헬멧 상태:", self.lbl_helmet)
        self.meta_layout.addRow("조끼 상태:", self.lbl_vest)
        self.meta_layout.addRow("위반 횟수:", self.lbl_violation_count)
        self.meta_layout.addRow("최초 감지:", self.lbl_first_seen)
        self.meta_layout.addRow("마지막 감지:", self.lbl_last_seen)
        self.meta_layout.addRow("대표 이미지 경로:", self.lbl_frame_path)
        layout.addLayout(self.meta_layout)

    def clear_detail(self, message: str = "선택된 추적 결과가 없습니다"):
        self.title_label.setText("추적 결과 상세")
        self.image_label.clear()
        self.image_label.setText(message)
        for label in (
            self.lbl_track_id,
            self.lbl_employee_no,
            self.lbl_ocr_confirmed,
            self.lbl_ocr_text,
            self.lbl_ocr_confidence,
            self.lbl_overall,
            self.lbl_helmet,
            self.lbl_vest,
            self.lbl_violation_count,
            self.lbl_first_seen,
            self.lbl_last_seen,
            self.lbl_frame_path,
        ):
            label.setText("-")

    def set_track_detail(self, track: dict):
        if not track:
            self.clear_detail()
            return

        track_id = track.get("track_id") or "-"
        self.title_label.setText(f"추적 결과 상세 [Track {track_id}]")
        self.lbl_track_id.setText(str(track_id))
        self.lbl_employee_no.setText(str(track.get("employee_no") or "-"))
        self.lbl_ocr_confirmed.setText("Y" if track.get("ocr_confirmed") else "N")
        self.lbl_ocr_text.setText(str(track.get("latest_ocr_text") or "-"))
        confidence = track.get("latest_ocr_confidence")
        self.lbl_ocr_confidence.setText("-" if confidence in (None, "") else str(confidence))
        self.lbl_overall.setText(self._map_overall(track.get("overall_ppe_status")))
        self.lbl_helmet.setText(self._map_item(track.get("helmet_status")))
        self.lbl_vest.setText(self._map_item(track.get("vest_status")))
        self.lbl_violation_count.setText(str(track.get("violation_count") or 0))
        self.lbl_first_seen.setText(self._format_seen(track.get("first_seen_frame_no"), track.get("first_seen_at_sec")))
        self.lbl_last_seen.setText(self._format_seen(track.get("last_seen_frame_no"), track.get("last_seen_at_sec")))
        frame_path = track.get("representative_frame_path") or "-"
        self.lbl_frame_path.setText(str(frame_path))
        self._set_image(frame_path)

    def _set_image(self, frame_path: str | None):
        self.image_label.clear()
        resolved_path = self._resolve_frame_path(frame_path)
        if not resolved_path:
            self.image_label.setText("대표 프레임이 없습니다")
            return

        pixmap = QPixmap(resolved_path)
        if pixmap.isNull():
            self.image_label.setText("대표 프레임을 불러올 수 없습니다")
            return

        self.image_label.setPixmap(
            pixmap.scaled(
                self.image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    @staticmethod
    def _map_overall(value: str | None) -> str:
        mapping = {
            "COMPLIANT": "정상",
            "NON_COMPLIANT": "위반",
            "UNKNOWN": "미확인",
        }
        return mapping.get(str(value or "").upper(), "-")

    @staticmethod
    def _map_item(value: str | None) -> str:
        mapping = {
            "WORN": "착용",
            "WEARING": "착용",
            "NOT_WORN": "미착용",
            "NOT_WEARING": "미착용",
            "UNKNOWN": "미확인",
        }
        return mapping.get(str(value or "").upper(), "-")

    @staticmethod
    def _format_seen(frame_no, time_sec) -> str:
        frame_label = "-" if frame_no in (None, "") else f"f{frame_no}"
        time_label = "-" if time_sec in (None, "") else f"{time_sec}s"
        return f"{frame_label} / {time_label}"

    @staticmethod
    def _resolve_frame_path(frame_path: str | None) -> str | None:
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
