from ...domain.entities.analysis_session import AnalysisSession
from ...domain.ports.repository import AnalysisSessionRepository

class GetAnalysisSessionUseCase:
    def __init__(self, session_repo: AnalysisSessionRepository):
        self.session_repo = session_repo

    def execute(self, session_id: str) -> AnalysisSession | None:
        return self.session_repo.find_by_session_id(session_id)
