from app.application.dtos import AnalysisSessionListResponseDto, AnalysisSessionResponseDto


class GetRecentSessionsUseCase:
    def __init__(self, session_repo):
        self.session_repo = session_repo

    def execute(self, limit: int = 20):
        sessions = self.session_repo.find_recent(limit)
        return AnalysisSessionListResponseDto(
            sessions=[
                AnalysisSessionResponseDto(
                    session_no=session.id,
                    session_id=session.session_id,
                    source_type=session.source_type.value,
                    source_name=session.source_name,
                    status=session.status.value,
                    frame_interval_sec=session.frame_interval_sec,
                    total_frames=session.total_frames,
                    processed_frames=session.processed_frames,
                    detected_count=session.detected_count,
                    requested_by=session.requested_by,
                    started_at=session.started_at,
                    finished_at=session.finished_at,
                    fail_reason=session.fail_reason,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                )
                for session in sessions
            ]
        )
