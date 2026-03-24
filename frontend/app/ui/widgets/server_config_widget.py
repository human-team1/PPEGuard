from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox, QGroupBox
)
from PySide6.QtCore import Signal, Slot
from app.config.settings import AppSettings
from app.services.api_client import ApiClient

class ServerConfigWidget(QGroupBox):
    # 연결 성공 여부를 상위 부모로 전달하기 위한 커스텀 시그널
    connection_status_changed = Signal(bool)

    def __init__(self, settings: AppSettings, api_client: ApiClient, parent=None):
        super().__init__("서버 연결", parent)
        self.settings = settings
        self.api_client = api_client
        self.is_connected = False
        self._init_ui()
        
    def _init_ui(self):
        layout = QHBoxLayout()
        
        self.url_input = QLineEdit()
        # [변경: placeholder와 기본값을 5000 포트로 유도]
        self.url_input.setPlaceholderText("예: http://127.0.0.1:5000")
        
        # QSettings에 저장된 주소가 있으면 그걸 쓰고, 없으면 5000 기본으로 채웁니다.
        current_url = self.settings.get_server_url()
        self.url_input.setText(current_url)
        
        self.connect_btn = QPushButton("연결 테스트")
        self.connect_btn.clicked.connect(self._test_connection)
        
        self.status_label = QLabel("상태: 미확인")
        self.status_label.setStyleSheet("color: gray;")
        
        layout.addWidget(QLabel("서버 주소:"))
        layout.addWidget(self.url_input)
        layout.addWidget(self.connect_btn)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        # URL 변경 시 상태를 '미확인'으로 리셋
        self.url_input.textChanged.connect(self._reset_status)
        
    def _reset_status(self):
        self.is_connected = False
        self.status_label.setText("상태: 미확인")
        self.status_label.setStyleSheet("color: gray;")
        self.connection_status_changed.emit(False)
        
    @Slot()
    def _test_connection(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "경고", "서버 주소를 입력해주세요.")
            return
            
        self.status_label.setText("상태: 확인 중...")
        self.status_label.setStyleSheet("color: orange;")
        self.connect_btn.setEnabled(False)
        
        # API Client 갱신
        self.api_client.update_base_url(url)
        
        try:
            # [추가: 실시간 분석을 위한 소켓 주소도 함께 5000 등 입력된 포트로 동적 업데이트 필요 시점]
            # (현재는 ApiClient의 health check를 먼저 수행)
            res = self.api_client.check_health()
            if res.get("status") == "healthy":
                self.is_connected = True
                self.status_label.setText("상태: 연결 성공")
                self.status_label.setStyleSheet("color: green;")
                self.settings.save_server_url(url)
                QMessageBox.information(self, "성공", "서버와 정상적으로 연결되었습니다.")
            else:
                raise ValueError("서버 응답 형식이 올바르지 않습니다.")
        except Exception as e:
            self.is_connected = False
            self.status_label.setText("상태: 연결 실패")
            self.status_label.setStyleSheet("color: red;")
            # 에러 메시지의 포트 번호를 확인하여 사용자에게 가이드 유도
            QMessageBox.critical(self, "오류", f"연결 테스트 실패(포트 {url} 확인 요망):\n{str(e)}")
        finally:
            self.connect_btn.setEnabled(True)
            self.connection_status_changed.emit(self.is_connected)
