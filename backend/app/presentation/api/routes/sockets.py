import os
import time 
import torch 
from flask_socketio import emit
from app import socketio

from app.application.dtos import AnalyzeFrameCommand
from app.application.services.analyze_worker_service import AnalyzeWorker
from app.application.usecases.analyze_frame_usecase import AnalyzeFrameUseCase
from app.application.usecases.process_detection_result import ProcessDetectionResultUseCase
from app.infrastructure.ai_analyzer.yolo_detector import YoloDetector
from app.infrastructure.service_db.repositories.analysis_session_repository import SQLAlchemyAnalysisSessionRepository
from app.infrastructure.service_db.repositories.analysis_frame_repository import SQLAlchemyAnalysisFrameRepository
from app.infrastructure.service_db.repositories.detection_result_repository import SQLAlchemyDetectionResultRepository

# [필수 패치: eventlet 환경에서의 PyTorch 연산 지연 방지]
torch.set_num_threads(1)

# AI 엔진 및 유스케이스 초기화 (Presentation Layer)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# MODEL_PATH = os.path.join(BASE_DIR, "../../../infrastructure/ai_analyzer/models/best.pt")
MODEL_PATH = os.path.join(BASE_DIR, "../../../infrastructure/ai_analyzer/models/yolo11s_ft_aug_best.pt")
TRACKER_CONFIG = os.path.join(BASE_DIR, "../../../infrastructure/ai_analyzer/configs/bytetrack.yaml")

detector = YoloDetector(MODEL_PATH, TRACKER_CONFIG)
worker = AnalyzeWorker(detector)

# [Step 2 지원] 리포지토리 및 프로세스 유스케이스 초기화
session_repo = SQLAlchemyAnalysisSessionRepository()
frame_repo = SQLAlchemyAnalysisFrameRepository()
result_repo = SQLAlchemyDetectionResultRepository()

process_result_usecase = ProcessDetectionResultUseCase(
    session_repo=session_repo,
    frame_repo=frame_repo,
    result_repo=result_repo,
    customer_result_repo=None # 고객 DB 연동은 환경 설정에 따라 추가 필요
)

analyze_frame_usecase = AnalyzeFrameUseCase(worker, process_result_usecase=process_result_usecase)

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
        command = AnalyzeFrameCommand(
            image_base64=image_data,
            session_id=data.get('session_id')
        )
        
        # [UseCase]: 비즈니스 로직 실행 (전처리 로직은 UseCase가 Service를 사용하여 내부적으로 처리)
        results = analyze_frame_usecase.execute(command)
        
        # [Presentation]: 결과 데이터 직렬화 및 스트리밍 전송
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

        emit('results', {'persons': serialized_results})
        
    except Exception as e:
        print(f"[ERR] 통신/분석 에러: {e}", flush=True)
        emit('error', {'message': f"분석 중 오류 발생: {str(e)}"})

@socketio.on('disconnect')
def handle_disconnect():
    print("[DISC] 실시간 분석 세션 종료", flush=True)
