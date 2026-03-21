from PySide6.QtCore import QThread, Signal
from typing import Callable, Any

class ApiWorker(QThread):
    """네트워크 통신 중 메인 UI 스레드가 멈추지 않도록 돕는 태스크 워커"""
    result_ready = Signal(object)
    error_occurred = Signal(str)

    def __init__(self, func: Callable, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.result_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))
