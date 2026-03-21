from datetime import datetime
from ...domain.entities.analysis_session import AnalysisSession, AnalysisSessionStatus
from ...domain.ports.repository import AnalysisSessionRepository

class CompleteAnalysisSessionUseCase:
    def __init__(self, session_repo: AnalysisSessionRepository):
        self.session_repo = session_repo

    def execute(self, session_id: str, processed_frames: int) -> AnalysisSession:
        session = self.session_repo.find_by_session_id(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        now = datetime.now()
        session.status = AnalysisSessionStatus.COMPLETED
        session.processed_frames = processed_frames
        session.finished_at = now
        session.updated_at = now
        
        self.session_repo.update(session)
        return session
