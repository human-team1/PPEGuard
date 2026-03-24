from typing import Dict
from ..dtos import AnalyzeFrameCommand
from ..services.analyze_worker_service import AnalyzeWorker
from ...domain.entities.person import Person

class AnalyzeFrameUseCase:
    """
    [실시간 소켓 전용 유스케이스]
    - Presentation(소켓 핸들러)으로부터 전달받은 DTO(AnalyzeFrameCommand)를 비즈니스 로직으로 변환하여 실행합니다.
    - 데이터 전처리는 주입받은 AnalyzeWorker(Service)에 위임합니다.
    """
    def __init__(self, analyze_worker: AnalyzeWorker):
        self.analyze_worker = analyze_worker

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
        
        return results
