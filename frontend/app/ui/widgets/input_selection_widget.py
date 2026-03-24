from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QRadioButton, QPushButton, QLabel, QFileDialog, QMessageBox
)
from PySide6.QtCore import Signal, Qt
from app.ui.widgets.webcam_preview_widget import WebcamPreviewWidget

class InputSelectionWidget(QGroupBox):
    analysis_requested = Signal(str, str) # source_type, source_val

    def __init__(self, parent=None):
        super().__init__("모드 선택", parent)
        self.selected_file_path = None
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        # 1. 입력 모드 선택 라디오 버튼
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
        
        # 2. 파일 선택 영역
        self.file_picker_widget = QWidget()
        file_layout = QHBoxLayout(self.file_picker_widget)
        file_layout.setContentsMargins(0, 0, 0, 0)
        self.file_path_label = QLabel("선택된 파일 없음")
        self.file_path_label.setStyleSheet("color: gray; font-size: 10px;")
        self.file_select_btn = QPushButton("영상 선택...")
        self.file_select_btn.setMaximumWidth(80)
        self.file_select_btn.clicked.connect(self._select_file)
        file_layout.addWidget(self.file_path_label, stretch=1)
        file_layout.addWidget(self.file_select_btn)
        layout.addWidget(self.file_picker_widget)
        
        # 2b. 웹캠 미리보기 영역 (최대 높이 제한)
        self.webcam_preview = WebcamPreviewWidget()
        self.webcam_preview.setMaximumHeight(180)
        self.webcam_preview.hide()
        layout.addWidget(self.webcam_preview)
        
        # 3. 분석 시작 버튼
        start_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶ 분석 시작")
        self.start_btn.setMinimumHeight(38)
        self.start_btn.setEnabled(False) 
        self.start_btn.setStyleSheet(
            "font-weight: bold; font-size: 12px; "
            "background-color: #4CAF50; color: white; border-radius: 4px;"
        )
        self.start_btn.clicked.connect(self._on_start_clicked)
        start_layout.addWidget(self.start_btn)
        layout.addLayout(start_layout)
        
        layout.addStretch()
        self.setLayout(layout)
        
    def _on_mode_changed(self):
        if self.radio_file.isChecked():
            self.webcam_preview.stop_camera()
            self.webcam_preview.hide()
            self.file_picker_widget.show()
            self._update_start_button_state()
        else:
            self.file_picker_widget.hide()
            self.webcam_preview.show()
            self.webcam_preview.start_camera(camera_id=0)
            self._update_start_button_state()
            
    def _select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "동영상 파일 선택", "", "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv)"
        )
        if file_path:
            self.selected_file_path = file_path
            # 파일명만 표시 (경로가 길 경우 생략)
            import os
            display_name = os.path.basename(file_path)
            if len(display_name) > 25:
                display_name = display_name[:22] + "..."
            self.file_path_label.setText(display_name)
            self.file_path_label.setStyleSheet("color: green; font-size: 10px; font-weight: bold;")
            self.file_path_label.setToolTip(file_path)
            self._update_start_button_state()
            
    def _update_start_button_state(self):
        if self.radio_file.isChecked():
            self.start_btn.setEnabled(bool(self.selected_file_path))
        else:
            self.start_btn.setEnabled(True) # 웹캠은 즉시 분석 시작 버튼 오픈
            
    def set_server_connected(self, is_connected: bool):
        self.is_server_connected = is_connected
        
    def _on_start_clicked(self):
        if hasattr(self, 'is_server_connected') and not self.is_server_connected:
            QMessageBox.warning(self, "경고", "분석을 요청하기 전에 먼저 서버에 성공적으로 연결해주세요.")
            return

        # 라디오 버튼 분기에 따라 외부로 시작 시그널 전송
        if self.radio_file.isChecked():
            self.analysis_requested.emit("VIDEO_FILE", self.selected_file_path)
        else:
            self.analysis_requested.emit("WEBCAM", "0")
