import os
import time 
import torch 
from flask_socketio import emit
from app import socketio

from app.application.dtos import AnalyzeFrameCommand
from app.application.services.analyze_worker_service import AnalyzeWorker
from app.application.usecases.analyze_frame_usecase import AnalyzeFrameUseCase
from app.infrastructure.ai_analyzer.yolo_detector import YoloDetector

# [필수 패치: eventlet 환경에서의 PyTorch 연산 지연 방지]
torch.set_num_threads(1)

# AI 엔진 및 유스케이스 초기화 (Presentation Layer)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "../../../infrastructure/ai_analyzer/models/best.pt")
TRACKER_CONFIG = os.path.join(BASE_DIR, "../../../infrastructure/ai_analyzer/configs/bytetrack.yaml")

detector = YoloDetector(MODEL_PATH, TRACKER_CONFIG)
worker = AnalyzeWorker(detector)
analyze_frame_usecase = AnalyzeFrameUseCase(worker)

@socketio.on('connect')
def handle_connect():
    print("[CONN] 실시간 분석 클라이언트가 접속했습니다.", flush=True)

@socketio.on('frame')
def handle_frame(data):
    """
    [Socket.IO 전송 핸들러 - Presentation Layer]
    1. 데이터를 받아 DTO(AnalyzeFrameCommand)로 캡슐화
    2. UseCase(AnalyzeFrameUseCase)를 실행하여 분석 요청
    3. 도메인 엔티티(Person) 결과를 받아 최종 Serializing 하여 전달
    """
    ts_start = time.time()
    try:
        image_data = data.get('image')
        if not image_data:
            return

        # [Presentation]: 입력을 DTO로 묶어 전달 (계층간 통과 규범)
        command = AnalyzeFrameCommand(image_base64=image_data)
        
        # [UseCase]: 비즈니스 로직 실행 (전처리 로직은 UseCase가 Service를 사용하여 내부적으로 처리)
        results = analyze_frame_usecase.execute(command)
        
        # [Presentation]: 결과 데이터 직렬화 및 스트리밍 전송
        serialized_results = []


        # --- [로그 추가 구간 시작] ---
        # print(f"\n[AI 분석 시작] 수신 데이터 크기: {len(image_data) // 1024} KB", flush=True)
        # -------


        for p_id, person in results.items():
            status = "안전" if person.is_safe() else "위험(장구류 미착용)"
            # print(f"  └ ID: {person.id} | 결과: {status} | Helmet: {person.has_helmet} | Vest: {person.has_vest}", flush=True)
            serialized_results.append({
                'id': person.id,
                'bbox': person.bbox,
                'has_vest': person.has_vest,
                'has_helmet': person.has_helmet,
                'is_safe': person.is_safe(),
                'confidence': float(person.confidence)
            })

        emit('results', {'persons': serialized_results})
        
        latency = (time.time() - ts_start) * 1000
        # print(f"[RESULT] 감지 인원: {len(serialized_results)}명 | 처리시간: {latency:.2f}ms", flush=True)

    except Exception as e:
        print(f"[ERR] 통신/분석 에러: {e}", flush=True)
        emit('error', {'message': f"분석 중 오류 발생: {str(e)}"})

@socketio.on('disconnect')
def handle_disconnect():
    print("[DISC] 실시간 분석 세션 종료", flush=True)
