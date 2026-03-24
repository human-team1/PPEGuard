from datetime import datetime
from decimal import Decimal

from ...domain.entities.analysis_frame import AnalysisFrame, FrameProcessingStatus
from ...domain.ports.repository import AnalysisFrameRepository


class CreateAnalysisFrameUseCase:
    def __init__(self, frame_repo: AnalysisFrameRepository):
        self.frame_repo = frame_repo

    def execute(
        self,
        session_id: int,
        frame_no: int,
        frame_time_sec: float,
        person_count: int = 0,
        frame_image_path: str = None,
        processing_status: FrameProcessingStatus = FrameProcessingStatus.PROCESSED,
        error_message: str = None,
    ) -> AnalysisFrame:
        now = datetime.now()

        frame = AnalysisFrame(
            session_id=session_id,
            frame_no=frame_no,
            frame_time_sec=Decimal(str(frame_time_sec)),
            captured_at=now,
            frame_image_path=frame_image_path,
            person_count=person_count,
            processing_status=processing_status,
            error_message=error_message,
            created_at=now,
            updated_at=now,
        )

        self.frame_repo.save(frame)
        return frame