import uuid
from datetime import datetime

from ...domain.entities.analysis_session import (
    AnalysisSession,
    AnalysisSessionStatus,
    AnalysisSourceType,
)
from ...domain.ports.repository import AnalysisSessionRepository
from ..dtos import StartSessionCommand


class StartAnalysisSessionUseCase:
    def __init__(self, session_repo: AnalysisSessionRepository):
        self.session_repo = session_repo

    def execute(self, cmd: StartSessionCommand) -> AnalysisSession:
        now = datetime.now()
        status = AnalysisSessionStatus.QUEUED
        started_at = None

        if cmd.source_type == AnalysisSourceType.WEBCAM:
            status = AnalysisSessionStatus.PROCESSING
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
            started_at=started_at,
            video_started_at=cmd.video_started_at or now,
        )
        self.session_repo.save(session)
        return session
