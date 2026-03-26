import logging

from ..dtos import AnalyzeFrameCommand


logger = logging.getLogger(__name__)


class AnalyzeFrameUseCase:
    def __init__(
        self,
        webcam_pipeline_manager,
        realtime_event_service=None,
    ):
        self.webcam_pipeline_manager = webcam_pipeline_manager
        self.realtime_event_service = realtime_event_service

    def execute(self, command: AnalyzeFrameCommand) -> None:
        if not command.session_id:
            logger.warning("[Webcam] frame skipped missing_session_id")
            return

        self.webcam_pipeline_manager.submit_frame(
            session_id=command.session_id,
            image_base64=command.image_base64,
            frame_no=command.frame_no,
        )

    def finalize_session(self, session_id: str, reason: str = "finalize") -> None:
        if not session_id:
            return

        if self.realtime_event_service:
            self.realtime_event_service.emit_session_status(
                session_id=session_id,
                source_type="WEBCAM",
                status="stopping",
            )

        self.webcam_pipeline_manager.finalize_session(
            session_id=session_id,
            reason=reason,
        )
