from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class DashboardBarChartWidget(QGroupBox):
    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self.content_layout = QVBoxLayout(self)
        self.empty_label = QLabel("표시할 데이터가 없습니다.")
        self.empty_label.setStyleSheet("font-size: 11px; color: #777;")
        self.content_layout.addWidget(self.empty_label)

    def set_series(self, data: dict[str, int]):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not data:
            self.content_layout.addWidget(self.empty_label)
            return

        max_value = max(data.values()) or 1
        for label, value in data.items():
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)

            title = QLabel(label)
            title.setMinimumWidth(90)
            progress = QProgressBar()
            progress.setRange(0, max_value)
            progress.setValue(value)
            progress.setTextVisible(False)
            number = QLabel(str(value))
            number.setMinimumWidth(24)

            row_layout.addWidget(title)
            row_layout.addWidget(progress, stretch=1)
            row_layout.addWidget(number)
            self.content_layout.addWidget(row)
