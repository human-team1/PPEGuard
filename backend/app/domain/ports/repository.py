import abc
from ..entities.analysis_session import AnalysisSession
from ..entities.analysis_frame import AnalysisFrame
from ..entities.detection_result import DetectionResult

class AnalysisSessionRepository(abc.ABC):
    @abc.abstractmethod
    def save(self, session: AnalysisSession):
        pass

    @abc.abstractmethod
    def find_by_session_id(self, session_id: str):
        pass

    @abc.abstractmethod
    def update(self, session: AnalysisSession):
        pass

class AnalysisFrameRepository(abc.ABC):
    @abc.abstractmethod
    def save(self, frame: AnalysisFrame):
        pass

    @abc.abstractmethod
    def update(self, frame: AnalysisFrame):
        pass

    @abc.abstractmethod
    def find_by_id(self, frame_id: int): # analysis_session.id (내부 PK) 기준으로 frame 목록 조회
        pass

    @abc.abstractmethod
    def find_by_session_id(self, session_id: int):
        pass

class DetectionResultRepository(abc.ABC):
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
    def find_recent(self, limit: int):
        pass


