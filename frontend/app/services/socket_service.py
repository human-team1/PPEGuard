import base64
import cv2
import numpy as np
import socketio
from PySide6.QtCore import QObject, Signal

class SocketService(QObject):
    """
    백엔드 Flask-SocketIO 서버와 실시간 통신을 담당 (PySide6용)
    """
    results_ready = Signal(dict)
    connected = Signal()
    disconnected = Signal()
    error_occurred = Signal(str)

    # [최종 연동: 12345, 5000번 대신 5000번 포트 사용]
    def __init__(self, server_url: str = "http://127.0.0.1:5000"):
        super().__init__()
        self.server_url = server_url
        self.sio = socketio.Client()
        self.is_busy = False 
        self.session_id = None # 분석 세션 ID 연동용
        self._setup_handlers()

    def _setup_handlers(self):
        @self.sio.on('connect')
        def on_connect():
            # [최적화: 연결 시 Polling 방식보다 WebSocket 방식을 우선 권장]
            print(f"Connected to {self.server_url} via {self.sio.transport}", flush=True)
            self.connected.emit()

        @self.sio.on('disconnect')
        def on_disconnect():
            self.is_busy = False
            self.disconnected.emit()

        @self.sio.on('results')
        def on_results(data):
            # [최적화: 응답이 오면 다음 프레임을 보낼 수 있게 해제]
            self.is_busy = False
            self.results_ready.emit(data)

        @self.sio.on('error')
        def on_error(data):
            self.is_busy = False
            self.error_occurred.emit(data.get('message', '알 수 없는 오류'))

    def connect_server(self):
        try:
            if not self.sio.connected:
                # [강제: transport는 websocket과 polling을 모두 지원하도록 설정]
                self.sio.connect(self.server_url, transports=['websocket', 'polling'])
        except Exception as e:
            self.error_occurred.emit(f"서버 연결 실패: {str(e)}")

    def disconnect_server(self):
        self.is_busy = False
        if self.sio.connected:
            self.sio.disconnect()

    def send_frame(self, frame_np: np.ndarray):
        # [최적화: 분석 진행 중엔 이전 결과 수신 전까지 추가 전송 차단]
        if not self.sio.connected or self.is_busy:
            return

        try:
            self.is_busy = True 
            
            # 리사이징 (AI 분석용 가로 640px)
            h, w = frame_np.shape[:2]
            target_width = 640
            if w > target_width:
                aspect_ratio = h / w
                frame_np = cv2.resize(frame_np, (target_width, int(target_width * aspect_ratio)))

            # JPEG 압축 (품질 60)
            _, buffer = cv2.imencode('.jpg', frame_np, [cv2.IMWRITE_JPEG_QUALITY, 60])
            b64_frame = base64.b64encode(buffer).decode('utf-8')
            
            # [Step 2 지원] session_id와 함께 프레임 전송
            self.sio.emit('frame', {
                'image': f"data:image/jpeg;base64,{b64_frame}",
                'session_id': self.session_id
            })
        except Exception as e:
            self.is_busy = False
            print(f"Frame encoding error: {e}")
