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
        self._init_ui()
        
    def _init_ui(self):
        layout = QHBoxLayout(self)
        
        # 좌측: 목록 및 제어
        left_layout = QVBoxLayout()
        self.refresh_btn = QPushButton("서버에서 최신 결과 불러오기")
        self.refresh_btn.setMinimumHeight(30)
        self.refresh_btn.clicked.connect(self.load_results)
        
        self.list_widget = ResultListWidget()
        self.list_widget.item_selected.connect(self._on_item_selected)
        
        left_layout.addWidget(self.refresh_btn)
        left_layout.addWidget(self.list_widget)
        
        # 우측: 단건 디테일 출력
        self.detail_widget = ResultDetailWidget()
        
        layout.addLayout(left_layout, stretch=1)
        layout.addWidget(self.detail_widget, stretch=2)
        
    def load_results(self):
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("데이터 로딩 중...")
        
        self.worker = ApiWorker(self.api_client.get_results, limit=50) # 최근 50건 조회
        self.worker.result_ready.connect(self._on_list_loaded)
        self.worker.error_occurred.connect(self._on_list_error)
        self.worker.start()
        
    def _on_list_loaded(self, raw_data: list):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("서버에서 최신 결과 불러오기")
        
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
        dto = DetectionResultDto.from_api(raw_data)
        self.detail_widget.set_detail(dto)
        
    def _on_detail_error(self, err_msg: str):
        self.detail_widget.show_error(err_msg)
