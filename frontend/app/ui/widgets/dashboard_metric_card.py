from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class DashboardMetricCard(QFrame):
    def __init__(self, title: str, value: str = "0", accent_color: str = "#1565C0", parent=None):
        super().__init__(parent)
        self.title_label = QLabel(title)
        self.value_label = QLabel(value)
        self._init_ui(accent_color)

    def _init_ui(self, accent_color: str):
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(
            "QFrame { background: #F8FBFF; border: 1px solid #D7E3F4; border-radius: 8px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        self.title_label.setStyleSheet("font-size: 11px; color: #546E7A; font-weight: bold;")
        self.value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.value_label.setStyleSheet(
            f"font-size: 22px; font-weight: bold; color: {accent_color};"
        )
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value: str):
        self.value_label.setText(value)
