from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget


class StatusWidget(QWidget):
    STATE_STYLES = {
        "대기": ("#555", False),
        "시작 요청중": ("#1976D2", True),
        "분석중": ("#1565C0", True),
        "종료 요청중": ("#EF6C00", True),
        "중지": ("#455A64", False),
        "실패": ("#D32F2F", False),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.set_analysis_state("대기")

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        header = QLabel("분석 상태")
        header.setStyleSheet("font-weight: bold; font-size: 11px; color: #333;")
        layout.addWidget(header)

        self.state_label = QLabel()
        self.state_label.setAlignment(Qt.AlignCenter)
        self.state_label.setStyleSheet("font-size: 13px; font-weight: bold; padding: 4px;")
        layout.addWidget(self.state_label)

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-size: 11px; color: #555; padding: 4px;")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximumHeight(5)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        layout.addStretch()

    def set_analysis_state(self, state: str, message: str | None = None):
        color, loading = self.STATE_STYLES.get(state, ("#555", False))
        self.state_label.setText(state)
        self.state_label.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {color}; padding: 4px;"
        )
        self.status_label.setText(message or state)
        self.status_label.setStyleSheet(
            f"font-size: 11px; color: {color}; padding: 4px;"
        )
        self.progress_bar.setVisible(loading)

    def show_loading(self, message: str):
        self.set_analysis_state("시작 요청중", message)

    def show_success(self, message: str):
        self.set_analysis_state("중지", message)

    def show_error(self, message: str):
        self.set_analysis_state("실패", message)

    def reset(self):
        self.set_analysis_state("대기", "분석을 시작할 수 있습니다.")
