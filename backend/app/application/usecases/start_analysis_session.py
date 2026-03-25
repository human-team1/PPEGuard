import uuid
from datetime import datetime
from ...domain.entities.analysis_session import AnalysisSession, AnalysisSessionStatus
from ...domain.ports.repository import AnalysisSessionRepository
from ..dtos import StartSessionCommand

class StartAnalysisSessionUseCase:
    def __init__(self, session_repo: AnalysisSessionRepository):
        self.session_repo = session_repo

    def execute(self, cmd: StartSessionCommand) -> AnalysisSession:
        now = datetime.now()
        status = AnalysisSessionStatus.QUEUED
        started_at = None
        
        # 실시간 웹캠은 별도의 비디오 분석 워커가 필요 없으므로 즉시 시작 상태로 설정
        if cmd.source_type == "WEBCAM":
            status = AnalysisSessionStatus.STARTED
            started_at = now

        session = AnalysisSession(
            session_id=str(uuid.uuid4()),
            source_type=cmd.source_type,
            status=status, 
            frame_interval_sec=cmd.frame_interval_sec,
            processed_frames=0,
            detected_count=0,
            created_at=now,
            updated_at=now,
            source_name=cmd.source_name,
            total_frames=cmd.total_frames,
            requested_by=cmd.requested_by,
            started_at=started_at
        )
        self.session_repo.save(session)
        return session
