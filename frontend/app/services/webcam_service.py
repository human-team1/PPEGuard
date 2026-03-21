import cv2
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

class WebcamService(QThread):
    """OpenCV를 이용해 영상을 캡처하고 프레임을 시그널로 전달하는 백그라운드 스레드"""
    frame_ready = Signal(QImage)
    error_occurred = Signal(str)

    def __init__(self, camera_id=0, parent=None):
        super().__init__(parent)
        self.camera_id = camera_id
        self._is_running = False
        self.capture = None

    def run(self):
        self._is_running = True
        self.capture = cv2.VideoCapture(self.camera_id)
        
        if not self.capture.isOpened():
            self.error_occurred.emit(f"카메라 장치(ID: {self.camera_id})를 열 수 없습니다.")
            self._is_running = False
            return
            
        while self._is_running:
            ret, frame = self.capture.read()
            if ret:
                # BGR -> RGB 포맷 변경
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                qt_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                self.frame_ready.emit(qt_img)
            else:
                self.error_occurred.emit("카메라에서 영상 프레임을 읽어올 수 없습니다.")
                break
                
        if self.capture:
            self.capture.release()

    def stop(self):
        self._is_running = False
        self.wait()
