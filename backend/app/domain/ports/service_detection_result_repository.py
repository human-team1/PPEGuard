import abc
from app.domain.entities.detection_result import DetectionResult

class ServiceDetectionResultRepository(abc.ABC):
    """내부 SQLite에 detection_result를 저장하기 위한 포트"""
    
    @abc.abstractmethod
    def save(self, result: DetectionResult):
        pass

    @abc.abstractmethod
    def find_by_id(self, result_id: int):
        pass

    @abc.abstractmethod
    def find_by_frame_id(self, frame_id: int):
        pass

    @abc.abstractmethod
    def find_by_session_id(self, session_id: int):
        pass

    @abc.abstractmethod
    def find_recent(self, limit: int):
        pass
