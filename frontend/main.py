import sys
import os
from PySide6.QtWidgets import QApplication

# 패스 등록 (app 모듈 내부 절대 경로 임포트 보장)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.ui.views.main_window import MainWindow

def main():
    app = QApplication(sys.path)
    # 폰트, 스타일 등 글로벌 속성 설정 가능
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
