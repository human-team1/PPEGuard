import logging
import os
import sys

from PySide6.QtCore import QSharedMemory
from PySide6.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.ui.views.main_window import MainWindow
from app.utils.logging_config import configure_logging


_SINGLE_INSTANCE_KEY = "PPEGuardDesktopClient"


def main():
    configure_logging(os.getenv("LOG_LEVEL", "INFO"))
    shared_memory = QSharedMemory(_SINGLE_INSTANCE_KEY)
    if shared_memory.attach():
        return 0
    if not shared_memory.create(1):
        return 0

    app = QApplication(sys.argv)
    logging.getLogger(__name__).info("[Frontend] started")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
