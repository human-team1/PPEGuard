import abc
from ..entities.analysis_session import AnalysisSession
from ..entities.detection_result import DetectionResult

class AnalysisSessionRepository(abc.ABC):
    @abc.abstractmethod
    def save(self, session: AnalysisSession) -> None:
        pass

    @abc.abstractmethod
    def find_by_session_id(self, session_id: str) -> AnalysisSession | None:
        pass

    @abc.abstractmethod
    def update(self, session: AnalysisSession) -> None:
        pass

class DetectionResultRepository(abc.ABC):
    @abc.abstractmethod
    def save(self, result: DetectionResult) -> None:
        pass

    @abc.abstractmethod
    def find_by_id(self, result_id: int) -> DetectionResult | None:
        pass

    @abc.abstractmethod
    def find_by_session_id(self, session_id: int) -> list[DetectionResult]:
        pass

    @abc.abstractmethod
    def find_recent(self, limit: int) -> list[DetectionResult]:
        pass
