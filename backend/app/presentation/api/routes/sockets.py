import base64
import cv2
import numpy as np
import os
import time 
import torch # [추가: 멀티스레드 충돌 방지 패치]
from flask_socketio import emit
from app import socketio
from app.application.services.analyze_worker_service import AnalyzeWorker
from app.infrastructure.ai_analyzer.yolo_detector import YoloDetector

# [필수 패치: eventlet 환경에서의 PyTorch 연산 지연(13초 등)을 방지]
torch.set_num_threads(1)

# AI 엔진 초기화
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "../../../infrastructure/ai_analyzer/models/best.pt")
TRACKER_CONFIG = os.path.join(BASE_DIR, "../../../infrastructure/ai_analyzer/configs/bytetrack.yaml")

detector = YoloDetector(MODEL_PATH, TRACKER_CONFIG)
worker = AnalyzeWorker(detector)

@socketio.on('connect')
def handle_connect():
    print("[CONN] 클라이언트가 WebSocket으로 접속했습니다.", flush=True)

@socketio.on('frame')
def handle_frame(data):
    """
    [지연 최소화 루프]
    """
    ts_start = time.time()
    try:
        image_data = data.get('image')
        if not image_data:
            return

        if ',' in image_data:
            image_data = image_data.split(',')[1]

        # 디코딩
        img_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return

        # AI 분석 가동
        results = worker.run_inference(frame)
        
        # 데이터 직렬화
        serialized_results = []
        for p_id, person in results.items():
            serialized_results.append({
                'id': person.id,
                'bbox': person.bbox,
                'has_vest': person.has_vest,
                'has_helmet': person.has_helmet,
                'is_safe': person.is_safe(),
                'confidence': float(person.confidence)
            })

        # 분석 결과 발송 (WebSocket)
        emit('results', {'persons': serialized_results})
        
        latency = (time.time() - ts_start) * 1000
        print(f"[AI] 분석 지연: {latency:.2f}ms", flush=True)

    except Exception as e:
        print(f"[ERR] 통신/분석 에러: {e}", flush=True)
        emit('error', {'message': f"분석 중 오류 발생: {str(e)}"})

@socketio.on('disconnect')
def handle_disconnect():
    print("[DISC] 접속 종료", flush=True)
