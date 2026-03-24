import cv2
import time
import numpy as np
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

class WebcamService(QThread):
    """
    [지연 최적화: OpenCV 카메라 버퍼 덤핑 로직 추가]
    - 하드웨어가 쌓아둔 오래된 프레임을 버리고 항상 '현재 시점'의 프레임만 전송하도록 유도
    """
    frame_ready = Signal(QImage)
    raw_frame_ready = Signal(np.ndarray)
    error_occurred = Signal(str)

    def __init__(self, camera_id=0, parent=None, fps_limit=1): # [최적화: 전송 주기 조정]
        super().__init__(parent)
        self.camera_id = camera_id
        self._is_running = False
        self.capture = None
        
        self.stride_sec = 1.0 / fps_limit
        self.last_sent_time = 0

    def run(self):
        self._is_running = True
        self.capture = cv2.VideoCapture(self.camera_id)
        
        if not self.capture.isOpened():
            self.error_occurred.emit(f"카메라 장치(ID: {self.camera_id})를 열 수 없습니다.")
            self._is_running = False
            return
            
        # [사유: 윈도우 환경에서 OpenCV의 기본 버퍼링(약 4-5프레임)에 의한 지연을 제거]
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        while self._is_running:
            # [최적화: Grab() 루프를 통해 버퍼에 쌓인 과거 프레임을 비워냅니다.]
            # 하드웨어 버퍼에 남아있는 오래된 이미지를 무시하고 가장 최신 데이터를 획득합니다.
            # (이 로직이 빠지면 실제 상황보다 0.5s~1s 뒤쳐진 영상을 분석하게 됩니다.)
            for _ in range(2): 
                self.capture.grab()

            ret, frame = self.capture.read() # 실제 가장 신선한(Fresh) 프레임을 읽음
            
            if ret:
                # UI 전시용 처리
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                qt_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                self.frame_ready.emit(qt_img.copy())

                # STRIDE 제어 (약 0.2초마다 전송)
                current_time = time.time()
                if current_time - self.last_sent_time >= self.stride_sec:
                    self.raw_frame_ready.emit(frame)
                    self.last_sent_time = current_time

            else:
                self.error_occurred.emit("카메라에서 영상 프레임을 읽어올 수 없습니다.")
                break
            
            time.sleep(0.005) 
                
        if self.capture:
            self.capture.release()

    def stop(self):
        self._is_running = False
        self.wait()
