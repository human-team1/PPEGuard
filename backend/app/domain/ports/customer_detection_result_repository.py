import abc
from app.domain.entities.detection_result import DetectionResult

class CustomerDetectionResultRepository(abc.ABC):
    """고객사 사내망 DB에 detection_result만 적재하기 위한 전용 포트"""
    
    @abc.abstractmethod
    def save(self, result: DetectionResult):
        """탐지 결과를 고객사 DB에 저장. 재처리를 위해 실패 시 내부적으로 기록할 수 있음"""
        pass
