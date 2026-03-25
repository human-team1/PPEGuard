from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class InspectionItemSettingsWidget(QGroupBox):
    selection_changed = Signal(list)

    def __init__(self, items_metadata: list[dict], selected_keys: list[str], parent=None):
        super().__init__("점검 항목 설정", parent)
        self.items_metadata = items_metadata
        self.selected_keys = set(selected_keys)
        self.checkboxes = {}
        self.summary_label = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        guide_label = QLabel("구현된 항목만 선택할 수 있습니다.")
        guide_label.setStyleSheet("font-size: 11px; color: #666;")
        layout.addWidget(guide_label)

        for item in self.items_metadata:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)

            checkbox = QCheckBox(item["label"])
            checkbox.setChecked(item["implemented"] and item["key"] in self.selected_keys)
            checkbox.setEnabled(item["implemented"])
            checkbox.setToolTip(item["description"])
            checkbox.toggled.connect(self._emit_selection_changed)
            self.checkboxes[item["key"]] = checkbox

            status_text = "" if item["implemented"] else "준비중"
            status_label = QLabel(status_text)
            status_label.setStyleSheet(
                "font-size: 10px; color: #B26A00; font-weight: bold;"
                if status_text
                else "font-size: 10px; color: #2E7D32;"
            )

            row_layout.addWidget(checkbox)
            row_layout.addStretch()
            row_layout.addWidget(status_label)
            layout.addWidget(row_widget)

        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("font-size: 11px; color: #444; padding-top: 4px;")
        layout.addWidget(self.summary_label)

        self._update_summary()

    def get_selected_keys(self) -> list[str]:
        return [
            item["key"]
            for item in self.items_metadata
            if item["implemented"] and self.checkboxes[item["key"]].isChecked()
        ]

    def get_selected_labels(self) -> list[str]:
        return [
            item["label"]
            for item in self.items_metadata
            if item["implemented"] and self.checkboxes[item["key"]].isChecked()
        ]

    def _emit_selection_changed(self):
        self._update_summary()
        self.selection_changed.emit(self.get_selected_keys())

    def _update_summary(self):
        labels = self.get_selected_labels()
        summary_text = ", ".join(labels) if labels else "선택 없음"
        self.summary_label.setText(f"현재 활성 항목: {summary_text}")
