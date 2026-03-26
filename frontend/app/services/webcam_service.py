import os
import time

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage


class WebcamService(QThread):
    frame_ready = Signal(QImage)
    raw_frame_ready = Signal(np.ndarray)
    error_occurred = Signal(str)
    stopped = Signal()

    def __init__(self, camera_id=0, parent=None, fps_limit=3):
        super().__init__(parent)
        self.camera_id = camera_id
        self._is_running = False
        self.capture = None
        configured_analysis_fps = float(
            os.getenv(
                "WEBCAM_ANALYSIS_FPS",
                os.getenv("WEBCAM_CAPTURE_FPS", str(fps_limit)),
            )
        )
        self.analysis_stride_sec = 1.0 / max(configured_analysis_fps, 0.1)
        self.last_sent_time = 0.0

    def run(self):
        self._is_running = True
        self.capture = cv2.VideoCapture(self.camera_id)

        if not self.capture.isOpened():
            self.error_occurred.emit(f"카메라 장치(ID: {self.camera_id})를 찾을 수 없습니다.")
            self._is_running = False
            return

        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        while self._is_running:
            for _ in range(2):
                self.capture.grab()

            ret, frame = self.capture.read()
            if not ret:
                self.error_occurred.emit("카메라에서 영상 프레임을 읽을 수 없습니다.")
                break

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qt_img = QImage(
                rgb_frame.data,
                w,
                h,
                bytes_per_line,
                QImage.Format_RGB888,
            )
            self.frame_ready.emit(qt_img.copy())

            current_time = time.time()
            if current_time - self.last_sent_time >= self.analysis_stride_sec:
                self.raw_frame_ready.emit(frame)
                self.last_sent_time = current_time

            time.sleep(0.005)

        if self.capture:
            self.capture.release()
            self.capture = None

        self.stopped.emit()

    def stop(self):
        self._is_running = False
        if self.isRunning():
            self.wait(2000)
