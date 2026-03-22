from PySide6.QtCore import QSettings

class AppSettings:
    """최근 사용한 서버 URL 등을 QSettings로 관리하는 유틸리티 클래스"""
    
    def __init__(self):
        self.settings = QSettings("PPEGuard", "DesktopClient")
        
    def get_server_url(self, default="http://127.0.0.1:5000"):
        return self.settings.value("server_url", default)
        
    def save_server_url(self, url: str):
        self.settings.setValue("server_url", url)
