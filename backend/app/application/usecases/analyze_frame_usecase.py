import time
import collections
from typing import Dict, Any, Optional
from ..dtos import AnalyzeFrameCommand, ProcessDetectionCommand
from ..services.analyze_worker_service import AnalyzeWorker
from ...domain.entities.person import Person
from ...domain.entities.detection_result import ItemWearStatus

class AnalyzeFrameUseCase:
    """
    [실시간 소켓 전용 유스케이스]
    - Presentation(소켓 핸들러)으로부터 전달받은 DTO(AnalyzeFrameCommand)를 비즈니스 로직으로 변환하여 실행합니다.
    - 데이터 전처리는 주입받은 AnalyzeWorker(Service)에 위임합니다.
    - [Step 2] 웹캠 세션에 대해 주기로 데이터를 집계하여 DB에 저장합니다.
    """
    def __init__(self, analyze_worker: AnalyzeWorker, process_result_usecase=None):
        self.analyze_worker = analyze_worker
        self.process_result_usecase = process_result_usecase
        
        # [Step 2 지원] 웹캠 전용 주기 세션별 버퍼 (메모리상 관리)
        self.webcam_buffers: Dict[str, Any] = {} # session_id -> {"start_time": float, "data": dict}

    def execute(self, command: AnalyzeFrameCommand) -> Dict[int, Person]:
        """
        1. 이미지 정규화(Base64 -> Frame)
        2. AI 추론 실행
        3. 실시간 추적 상태(Entity 리스트) 반환
        """
        # [Normalization]: 계층화 아키텍처 가이드에 따라 서비스 레이어에서 가공
        normalized_frame = self.analyze_worker.prepare_frame(command.image_base64)
        
        if normalized_frame is None:
            return {}

        # [Logic]: 분석 서비스를 통해 도메인 엔티티(Person) 상태 갱신
        results = self.analyze_worker.run_inference(normalized_frame)

        # [Log] 웹캠 프레임별 신뢰도 출력
        for p_id, person in results.items():
            print(f"      - [WebcamFrameLog] Person {p_id}: Helmet={person.helmet_confidence:.2f}, Vest={person.vest_confidence:.2f}")
        
        # [Step 2] 웹캠 세션 DB 저장 및 주기 정산
        if command.session_id and self.process_result_usecase:
            self._handle_webcam_aggregation(command.session_id, results)
        
        return results

    def _handle_webcam_aggregation(self, session_id: str, results: Dict[int, Person]):
        now = time.time()
        if session_id not in self.webcam_buffers:
            self.webcam_buffers[session_id] = {
                "start_time": now,
                "data": collections.defaultdict(list)
            }
        
        buffer = self.webcam_buffers[session_id]
        
        # 데이터 누적
        for p_id, person in results.items():
            # [Step 2 지원] 버퍼에 누적 (터미널 출력은 위 execute에서 수행)
            buffer["data"][p_id].append({
                "helmet_conf": person.helmet_confidence,
                "vest_conf": person.vest_confidence,
                "bbox": person.bbox,
                "has_helmet": person.has_helmet,
                "has_vest": person.has_vest
            })
            
        # 60초 경과 시 정산
        if now - buffer["start_time"] >= 10.0:
            print(f"[Webcam] 60초 주기 정산 시작 (Session: {session_id})")
            for p_id, frames in buffer["data"].items():
                if not frames: continue
                
                avg_helmet = sum(f['helmet_conf'] for f in frames) / len(frames)
                avg_vest = sum(f['vest_conf'] for f in frames) / len(frames)
                
                # [Log] 웹캠 정산 구간 평균 신뢰도 출력
                print(f"  ==> [WebcamAggregationLog] Person {p_id} (Data Count: {len(frames)}): "
                      f"Avg Helmet={avg_helmet:.4f}, Avg Vest={avg_vest:.4f}")
                
                # 대표값으로 마지막 프레임 데이터 사용 (간략화)
                last = frames[-1]
                cmd = ProcessDetectionCommand(
                    session_id=session_id,
                    frame_id=1, # 웹캠은 스트리밍이므로 임의의 프레임 ID 부여
                    person_index=p_id,
                    helmet_status=ItemWearStatus.WEARING if avg_helmet >= 0.7 else ItemWearStatus.NOT_WEARING,
                    vest_status=ItemWearStatus.WEARING if avg_vest >= 0.7 else ItemWearStatus.NOT_WEARING,
                    person_box_x=last['bbox'][0],
                    person_box_y=last['bbox'][1],
                    person_box_width=last['bbox'][2] - last['bbox'][0],
                    person_box_height=last['bbox'][3] - last['bbox'][1]
                )
                self.process_result_usecase.execute(cmd)
            
            # 버퍼 초기화
            self.webcam_buffers[session_id] = {
                "start_time": now,
                "data": collections.defaultdict(list)
            }
