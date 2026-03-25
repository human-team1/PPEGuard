from typing import List
from ...domain.entities.detection_result import DetectionResult
from ...domain.ports.repository import AnalysisSessionRepository, AnalysisFrameRepository
from ...domain.ports.service_detection_result_repository import ServiceDetectionResultRepository

class GetSessionResultsUseCase:
    def __init__(
        self, 
        session_repo: AnalysisSessionRepository, 
        result_repo: ServiceDetectionResultRepository,
        frame_repo: AnalysisFrameRepository
    ):
        self.session_repo = session_repo
        self.frame_repo = frame_repo
        self.result_repo = result_repo

    def execute(self, session_id: str) -> List[DetectionResult]:
        session = self.session_repo.find_by_session_id(session_id)
        if not session or session.id is None:
            raise ValueError(f"Session not found or has no internal id: {session_id}")

        results = self.result_repo.find_by_session_id(session.id)
        return results

    # def execute(self, session_id: str) -> List[DetectionResult]:
    #     session = self.session_repo.find_by_session_id(session_id)
    #     if not session or session.id is None:
    #         raise ValueError(f"Session not found or has no internal id: {session_id}")

    #     frames = self.frame_repo.find_by_session_id(session.id)

    #     results = []
    #     for frame in frames:
    #         frame_results = self.result_repo.find_by_frame_id(frame.id)
    #         results.extend(frame_results)

    #     return results
