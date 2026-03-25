from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLabel
from PySide6.QtCore import Signal, Qt
from typing import List
from app.models.result_dto import DetectionResultDto

class ResultListWidget(QWidget):
    item_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.empty_label = QLabel("불러온 결과 내역이 없습니다.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: gray; font-size: 14px;")
        
        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_widget.hide()
        
        layout.addWidget(self.empty_label)
        layout.addWidget(self.list_widget)
        
    def set_items(self, dtos: List[DetectionResultDto]):
        self.list_widget.clear()
        
        if not dtos:
            self.list_widget.hide()
            self.empty_label.show()
            return
        
        self.empty_label.hide()
        self.list_widget.show()
        
        for dto in dtos:
            item_text = f"[{dto.detected_at}] ID: {dto.id} | 종합 상태: {dto.overall_status}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, dto.id)
            self.list_widget.addItem(item)

    def _on_selection_changed(self):
        item = self.list_widget.currentItem()
        if item:
            result_id = item.data(Qt.UserRole)
            if result_id:
                self.item_selected.emit(str(result_id))