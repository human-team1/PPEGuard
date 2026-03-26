import os
import sys

from PySide6.QtCore import QSharedMemory
from PySide6.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.ui.views.main_window import MainWindow


_SINGLE_INSTANCE_KEY = "PPEGuardDesktopClient"


def main():
    shared_memory = QSharedMemory(_SINGLE_INSTANCE_KEY)
    if shared_memory.attach():
        return 0
    if not shared_memory.create(1):
        return 0

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
