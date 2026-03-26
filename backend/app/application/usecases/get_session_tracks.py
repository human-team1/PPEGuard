from app.application.dtos import AnalysisTrackSummaryListResponseDto, AnalysisTrackSummaryResponseDto
from app.domain.entities.analysis_session import AnalysisSourceType


class GetSessionTracksUseCase:
    def __init__(self, session_repo, track_summary_repo):
        self.session_repo = session_repo
        self.track_summary_repo = track_summary_repo

    def execute(self, session_id: str):
        session = self.session_repo.find_by_session_id(session_id)
        if session is None or session.id is None:
            raise ValueError("Analysis session not found")
        if session.source_type != AnalysisSourceType.WEBCAM:
            raise ValueError("Track summaries are available only for WEBCAM sessions")

        tracks = self.track_summary_repo.find_by_session_id(session.id)
        return AnalysisTrackSummaryListResponseDto(
            session_id=session.session_id,
            tracks=[self._to_dto(track) for track in tracks],
        )

    @staticmethod
    def _to_dto(track):
        return AnalysisTrackSummaryResponseDto(
            track_summary_id=track.id,
            track_id=track.track_id,
            representative_frame_id=track.representative_frame_id,
            representative_frame_path=track.best_image_path,
            employee_no=track.employee_no,
            latest_ocr_text=track.latest_ocr_text,
            latest_ocr_confidence=track.latest_ocr_confidence,
            ocr_confirmed=track.ocr_confirmed,
            overall_ppe_status=track.overall_ppe_status,
            helmet_status=track.helmet_status,
            vest_status=track.vest_status,
            violation_count=track.violation_count,
            first_seen_frame_no=track.first_seen_frame_no,
            last_seen_frame_no=track.last_seen_frame_no,
            first_seen_at_sec=track.first_seen_at_sec,
            last_seen_at_sec=track.last_seen_at_sec,
            created_at=track.created_at,
            updated_at=track.updated_at,
        )
