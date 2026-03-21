from typing import List
from ...domain.entities.detection_result import DetectionResult
from ...domain.ports.repository import AnalysisSessionRepository, DetectionResultRepository

class GetSessionResultsUseCase:
    def __init__(self, session_repo: AnalysisSessionRepository, result_repo: DetectionResultRepository):
        self.session_repo = session_repo
        self.result_repo = result_repo

    def execute(self, session_id: str) -> List[DetectionResult]:
        session = self.session_repo.find_by_session_id(session_id)
        if not session or session.id is None:
            raise ValueError(f"Session not found or has no internal id: {session_id}")
            
        return self.result_repo.find_by_session_id(session.id)
