from typing import Optional
from app.domain.entities.analysis_session import AnalysisSession
from app.domain.ports.repository import AnalysisSessionRepository

class InMemoryAnalysisSessionRepository(AnalysisSessionRepository):
    def __init__(self):
        self.sessions: dict[str, AnalysisSession] = {}

    def save(self, session: AnalysisSession):  
        self.sessions[session.session_id] = session

    def find_by_session_id(self, session_id: str): 
        return self.sessions.get(session_id)

    def update(self, session: AnalysisSession): 
        self.sessions[session.session_id] = session

    def find_recent(self, limit: int):
        sessions = list(self.sessions.values())
        sessions.sort(key=lambda item: item.created_at, reverse=True)
        return sessions[:limit]
