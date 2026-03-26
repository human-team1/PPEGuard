from PySide6.QtCore import QDateTime, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDateTimeEdit,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from app.config.inspection_items import INSPECTION_ITEMS
from app.ui.widgets.inspection_item_settings_widget import InspectionItemSettingsWidget
from app.ui.widgets.webcam_preview_widget import WebcamPreviewWidget


class InputSelectionWidget(QGroupBox):
    analysis_requested = Signal(str, str, object)
    analysis_stop_requested = Signal()
    inspection_items_changed = Signal(list)

    STATE_CONFIG = {
        "대기": {
            "start_text": "분석 시작",
            "stop_text": "분석 종료",
            "start_enabled": True,
            "stop_enabled": False,
            "accent": "#455A64",
            "message": "입력 대기 중입니다.",
        },
        "시작 요청중": {
            "start_text": "분석 시작 요청중...",
            "stop_text": "분석 종료",
            "start_enabled": False,
            "stop_enabled": False,
            "accent": "#1976D2",
            "message": "서버에 분석 시작을 요청했습니다.",
        },
        "분석중": {
            "start_text": "분석중",
            "stop_text": "분석 종료",
            "start_enabled": False,
            "stop_enabled": True,
            "accent": "#1565C0",
            "message": "실시간 분석이 진행 중입니다.",
        },
        "종료 요청중": {
            "start_text": "분석 시작",
            "stop_text": "종료 요청중...",
            "start_enabled": False,
            "stop_enabled": False,
            "accent": "#EF6C00",
            "message": "분석 종료를 요청했습니다.",
        },
        "중지": {
            "start_text": "다시 시작",
            "stop_text": "분석 종료",
            "start_enabled": True,
            "stop_enabled": False,
            "accent": "#455A64",
            "message": "분석을 중지했습니다.",
        },
        "실패": {
            "start_text": "분석 다시 시작",
            "stop_text": "분석 종료",
            "start_enabled": True,
            "stop_enabled": False,
            "accent": "#D32F2F",
            "message": "요청 처리 중 오류가 발생했습니다.",
        },
    }

    def __init__(self, selected_item_keys: list[str] | None = None, parent=None):
        super().__init__("입력 선택", parent)
        self.selected_file_path = None
        self.is_server_connected = False
        self.selected_item_keys = selected_item_keys or []
        self.current_state = "대기"
        self._init_ui()
        self.set_analysis_state("대기")

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(8)

        mode_label = QLabel("입력 소스 선택:")
        mode_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        layout.addWidget(mode_label)

        radio_layout = QHBoxLayout()
        self.radio_file = QRadioButton("동영상 파일")
        self.radio_webcam = QRadioButton("웹캠")
        self.radio_file.setChecked(True)
        self.radio_file.toggled.connect(self._on_mode_changed)
        radio_layout.addWidget(self.radio_file)
        radio_layout.addWidget(self.radio_webcam)
        radio_layout.addStretch()
        layout.addLayout(radio_layout)

        self.file_picker_widget = QWidget()
        file_layout = QHBoxLayout(self.file_picker_widget)
        file_layout.setContentsMargins(0, 0, 0, 0)
        self.file_path_label = QLabel("선택된 파일 없음")
        self.file_path_label.setStyleSheet("color: gray; font-size: 10px;")
        self.file_select_btn = QPushButton("영상 선택...")
        self.file_select_btn.setMaximumWidth(90)
        self.file_select_btn.clicked.connect(self._select_file)
        file_layout.addWidget(self.file_path_label, stretch=1)
        file_layout.addWidget(self.file_select_btn)
        layout.addWidget(self.file_picker_widget)

        self.time_checkbox = QCheckBox("영상 시작 시각 직접 입력")
        self.time_checkbox.stateChanged.connect(self._on_time_checkbox_changed)
        layout.addWidget(self.time_checkbox)

        self.time_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.time_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.time_edit.setCalendarPopup(True)
        self.time_edit.setEnabled(False)
        self.time_edit.setToolTip("미입력 시 서버 현재 시각을 사용합니다.")
        layout.addWidget(self.time_edit)

        self.webcam_preview = WebcamPreviewWidget()
        self.webcam_preview.hide()
        layout.addWidget(self.webcam_preview)

        self.inspection_settings_widget = InspectionItemSettingsWidget(
            INSPECTION_ITEMS,
            self.selected_item_keys,
        )
        self.inspection_settings_widget.selection_changed.connect(
            self.inspection_items_changed.emit
        )
        layout.addWidget(self.inspection_settings_widget)

        self.state_label = QLabel()
        self.state_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        layout.addWidget(self.state_label)

        self.hint_label = QLabel()
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet("font-size: 11px; color: #555;")
        layout.addWidget(self.hint_label)

        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("분석 시작")
        self.start_btn.setMinimumHeight(38)
        self.start_btn.clicked.connect(self._on_start_clicked)
        button_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("분석 종료")
        self.stop_btn.setMinimumHeight(38)
        self.stop_btn.clicked.connect(self.analysis_stop_requested.emit)
        button_layout.addWidget(self.stop_btn)
        layout.addLayout(button_layout)

        layout.addStretch()
        self.setLayout(layout)

    def get_selected_inspection_item_keys(self) -> list[str]:
        return self.inspection_settings_widget.get_selected_keys()

    def set_server_connected(self, is_connected: bool):
        self.is_server_connected = is_connected
        self.set_analysis_state(self.current_state)

    def set_analysis_state(self, state: str, detail_message: str | None = None):
        self.current_state = state
        config = self.STATE_CONFIG[state]
        self.state_label.setText(f"현재 상태: {state}")
        self.state_label.setStyleSheet(
            f"font-size: 12px; font-weight: bold; color: {config['accent']};"
        )
        self.hint_label.setText(detail_message or config["message"])
        self.start_btn.setText(config["start_text"])
        self.stop_btn.setText(config["stop_text"])

        can_start = config["start_enabled"] and self._can_start_in_current_mode()
        self.start_btn.setEnabled(can_start)
        self.stop_btn.setEnabled(config["stop_enabled"])

        self.start_btn.setStyleSheet(self._build_button_style("#2E7D32", can_start))
        self.stop_btn.setStyleSheet(
            self._build_button_style(config["accent"], config["stop_enabled"])
        )

    def _build_button_style(self, color: str, enabled: bool) -> str:
        background = color if enabled else "#B0BEC5"
        return (
            "font-weight: bold; font-size: 12px; color: white; border-radius: 4px; "
            f"background-color: {background}; padding: 8px;"
        )

    def _can_start_in_current_mode(self) -> bool:
        if not self.is_server_connected:
            return False
        if self.radio_file.isChecked():
            return bool(self.selected_file_path)
        return True

    def _on_mode_changed(self):
        if self.radio_file.isChecked():
            self.webcam_preview.stop_camera()
            self.webcam_preview.hide()
            self.file_picker_widget.show()
            self.time_checkbox.setEnabled(True)
        else:
            self.file_picker_widget.hide()
            self.webcam_preview.hide()
            self.webcam_preview.start_camera(camera_id=0)
            self.time_checkbox.setEnabled(False)
            self.time_edit.setEnabled(False)
        self.set_analysis_state(self.current_state)

    def _select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "동영상 파일 선택",
            "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv)",
        )
        if not file_path:
            return

        import os

        self.selected_file_path = file_path
        display_name = os.path.basename(file_path)
        if len(display_name) > 25:
            display_name = display_name[:22] + "..."
        self.file_path_label.setText(display_name)
        self.file_path_label.setStyleSheet(
            "color: green; font-size: 10px; font-weight: bold;"
        )
        self.file_path_label.setToolTip(file_path)
        self.set_analysis_state(self.current_state)

    def _on_time_checkbox_changed(self, state):
        self.time_edit.setEnabled(state == Qt.Checked)

    def _on_start_clicked(self):
        if not self.is_server_connected:
            QMessageBox.warning(self, "경고", "서버 연결 후 분석을 시작할 수 있습니다.")
            return

        if self.radio_file.isChecked():
            video_started_at = None
            if self.time_checkbox.isChecked():
                video_started_at = self.time_edit.dateTime().toString("yyyy-MM-ddTHH:mm:ss")
            self.analysis_requested.emit("VIDEO_FILE", self.selected_file_path, video_started_at)
            return

        self.analysis_requested.emit("WEBCAM", "0", None)
