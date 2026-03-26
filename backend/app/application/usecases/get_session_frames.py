from ..dtos import AnalysisFrameItemResponseDto, AnalysisFrameListResponseDto
from ...domain.ports.repository import AnalysisSessionRepository, AnalysisFrameRepository


class GetSessionFramesUseCase:
    def __init__(
        self,
        analysis_session_repository: AnalysisSessionRepository,
        analysis_frame_repository: AnalysisFrameRepository,
    ):
        self.analysis_session_repository = analysis_session_repository
        self.analysis_frame_repository = analysis_frame_repository

    def execute(self, session_id: str):
        session = self.analysis_session_repository.find_by_session_id(session_id)
        if session is None or session.id is None:
            raise ValueError("Analysis session not found")

        frames = self.analysis_frame_repository.find_by_session_id(session.id)

        return AnalysisFrameListResponseDto(
            session_id=session.session_id,
            frames=[
                AnalysisFrameItemResponseDto(
                    frame_id=frame.id,
                    frame_no=frame.frame_no,
                    frame_time_sec=frame.frame_time_sec,
                    captured_at=frame.captured_at,
                    frame_image_path=frame.frame_image_path,
                    frame_width=frame.frame_width,
                    frame_height=frame.frame_height,
                    person_count=frame.person_count,
                    processing_status=(
                        frame.processing_status.value
                        if hasattr(frame.processing_status, "value")
                        else str(frame.processing_status)
                    ),
                    error_message=frame.error_message,
                    created_at=frame.created_at,
                    updated_at=frame.updated_at,
                )
                for frame in frames
            ],
        )
