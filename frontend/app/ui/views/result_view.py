from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QMessageBox
from app.ui.widgets.result_list_widget import ResultListWidget
from app.ui.widgets.result_detail_widget import ResultDetailWidget
from app.services.api_client import ApiClient
from app.utils.async_task import ApiWorker
from app.models.result_dto import DetectionResultDto

class ResultView(QWidget):
    """결과 목록과 상세 패널을 한 화면에 조립한 종합 뷰"""
    def __init__(self, api_client: ApiClient, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.worker = None
        self.current_session_id = None 
        self._init_ui()
        
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(10)
        
        # 좌측: 목록 및 제어
        left_layout = QVBoxLayout()
        left_layout.setSpacing(5)
        
        self.refresh_btn = QPushButton("분석 내역 새로고침")
        self.refresh_btn.setMinimumHeight(30)
        self.refresh_btn.setStyleSheet("font-weight: bold;")
        self.refresh_btn.clicked.connect(self.load_results)
        
        self.list_widget = ResultListWidget()
        self.list_widget.item_selected.connect(self._on_item_selected)
        
        left_layout.addWidget(self.refresh_btn)
        left_layout.addWidget(self.list_widget, stretch=1)
        
        # 우측: 단건 디테일 출력
        self.detail_widget = ResultDetailWidget()
        
        layout.addLayout(left_layout, stretch=1)
        layout.addWidget(self.detail_widget, stretch=1)
    
    def set_session_id(self, session_id):
        self.current_session_id = session_id
        
    def load_results(self):
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("데이터 로딩 중...")

        if self.current_session_id:
            self.worker = ApiWorker(
                self.api_client.get_session_results,
                session_id=self.current_session_id,
            )
        else:
            self.worker = ApiWorker(
                self.api_client.get_results,
                limit=50,
            )

        self.worker.result_ready.connect(self._on_list_loaded)
        self.worker.error_occurred.connect(self._on_list_error)
        self.worker.start()
        
    def _on_list_loaded(self, raw_data: list):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("분석 결과 새로고침")
        
        # UI 충돌 방지용 DTO 매핑
        dtos = [DetectionResultDto.from_api(item) for item in raw_data]
        self.list_widget.set_items(dtos)
        
    def _on_list_error(self, err_msg: str):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("목록 로드 재시도")
        QMessageBox.warning(self, "목록 조회 오류", err_msg)
        
    def _on_item_selected(self, result_id: str):
        self.detail_widget.show_loading()
        
        self.worker = ApiWorker(self.api_client.get_result_detail, result_id=result_id)
        self.worker.result_ready.connect(self._on_detail_loaded)
        self.worker.error_occurred.connect(self._on_detail_error)
        self.worker.start()
        
    def _on_detail_loaded(self, raw_data: dict):
        print("detail raw_data =", raw_data)
        dto = DetectionResultDto.from_api(raw_data)
        print("dto.detected_at =", dto.detected_at)
        print("dto.image_path =", dto.image_path)
        self.detail_widget.set_detail(dto)
        
    def _on_detail_error(self, err_msg: str):
        self.detail_widget.show_error(err_msg)
