import uuid
from datetime import datetime
from typing import Optional
from ...domain.entities.analysis_session import AnalysisSession, AnalysisSessionStatus
from ...domain.ports.repository import AnalysisSessionRepository
from ..dtos import StartSessionCommand

class StartAnalysisSessionUseCase:
    def __init__(self, session_repo: AnalysisSessionRepository):
        self.session_repo = session_repo

    def execute(self, cmd: StartSessionCommand) -> AnalysisSession:
        now = datetime.now()
        session = AnalysisSession(
            session_id=str(uuid.uuid4()),
            source_type=cmd.source_type,
            status=AnalysisSessionStatus.QUEUED, # 요구사항에 맞춰 모든 세션은 생성 시 명시적으로 대기 상태
            frame_interval_sec=cmd.frame_interval_sec,
            processed_frames=0,
            detected_count=0,
            created_at=now,
            updated_at=now,
            source_name=cmd.source_name,
            total_frames=cmd.total_frames,
            requested_by=cmd.requested_by,
            started_at=None, # 큐에서 넘어갈 때 갱신되도록 처리
            video_started_at=cmd.video_started_at or now # 사용자 입력, 미입력 시 서버 현재 시각
           
        )
        self.session_repo.save(session)
        return session
