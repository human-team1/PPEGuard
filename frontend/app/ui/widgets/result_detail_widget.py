import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QFormLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from app.models.result_dto import DetectionResultDto

class ResultDetailWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        self.title_label = QLabel("결과 스냅샷 상세")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 10px;")
        layout.addWidget(self.title_label)
        
        self.image_label = QLabel("이미지 없음")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #eee; color: #888; border: 1px solid #ccc;")
        self.image_label.setMinimumSize(320, 240)
        layout.addWidget(self.image_label)
        
        self.info_layout = QFormLayout()
        self.lbl_video_time = QLabel("-")
        self.lbl_detected_at_absolute = QLabel("-")
        self.lbl_helmet = QLabel("-")
        self.lbl_vest = QLabel("-")
        self.lbl_ocr = QLabel("-")
        
        self.info_layout.addRow("영상 위치:", self.lbl_video_time)
        self.info_layout.addRow("발견 시각:", self.lbl_detected_at_absolute)
        self.info_layout.addRow("안전모 상태:", self.lbl_helmet)
        self.info_layout.addRow("작업조끼 상태:", self.lbl_vest)
        self.info_layout.addRow("OCR 텍스트:", self.lbl_ocr)
        
        layout.addLayout(self.info_layout)
        layout.addStretch()
        
    def show_loading(self):
        self.title_label.setText("데이터를 불러오는 중입니다...")
        self.title_label.setStyleSheet("color: blue; font-weight: bold; font-size: 16px;")
        self._clear_info()
        
    def show_error(self, message: str):
        self.title_label.setText(f"오류: {message}")
        self.title_label.setStyleSheet("color: red; font-weight: bold; font-size: 16px;")
        self._clear_info()
        
    def set_detail(self, dto: DetectionResultDto):
        self.title_label.setText(f"탐지 결과 [ID: {dto.id}]")
        self.title_label.setStyleSheet("color: black; font-weight: bold; font-size: 16px;")
        
        self.lbl_video_time.setText(dto.detected_at)
        self.lbl_detected_at_absolute.setText(dto.detected_at_absolute)
        self.lbl_helmet.setText(dto.helmet_status)
        self.lbl_vest.setText(dto.vest_status)
        self.lbl_ocr.setText(dto.ocr_text)
        
        if dto.image_path:
            pixmap = QPixmap(dto.image_path)
            if not pixmap.isNull():
                self.image_label.setPixmap(pixmap.scaled(
                    self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))
            else:
                self.image_label.clear()
                self.image_label.setText(f"이미지 읽기 불가\n({dto.image_path})")
        else:
            self.image_label.clear()
            self.image_label.setText("이미지 없음 (데이터 누락)")
            
    def _clear_info(self):
        self.lbl_video_time.setText("-")
        self.lbl_detected_at_absolute.setText("-")
        self.lbl_helmet.setText("-")
        self.lbl_vest.setText("-")
        self.lbl_ocr.setText("-")
        self.image_label.clear()
        self.image_label.setText("이미지 없음")