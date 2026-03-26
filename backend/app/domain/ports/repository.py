import abc
from ..entities.analysis_session import AnalysisSession
from ..entities.analysis_frame import AnalysisFrame
from ..entities.detection_result import DetectionResult
from ..entities.analysis_segment import AnalysisSegmentSummary, AnalysisSegmentPersonResult

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

    @abc.abstractmethod
    def delete_session_data(self, session_id: str):
        """(추가) 목적/이유: 분석 중단 시 해당 세션과 연관된 대용량 데이터(프레임, 세그먼트, 추론 결과 등)를 삭제하기 위한 인터페이스 정의"""
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


class AnalysisSegmentSummaryRepository(abc.ABC):
    @abc.abstractmethod
    def save(self, summary: AnalysisSegmentSummary):
        pass

    @abc.abstractmethod
    def find_by_session_id(self, session_id: int):
        pass


class AnalysisSegmentPersonResultRepository(abc.ABC):
    @abc.abstractmethod
    def save_many(self, results: list[AnalysisSegmentPersonResult]):
        pass

    @abc.abstractmethod
    def find_by_segment_summary_ids(self, segment_summary_ids: list[int]):
        pass


