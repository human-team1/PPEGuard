import logging

from app.application.services.best_frame_selector import BestFrameSelector
from app.application.services.segment_aggregation_service import SegmentAggregationService
from app.application.services.segment_window_service import SegmentWindowService


logger = logging.getLogger(__name__)


class SegmentResultService:
    def __init__(self, file_service, persistence_service, segment_seconds: float | None = None):
        self.file_service = file_service
        self.persistence_service = persistence_service
        self.window_service = SegmentWindowService(segment_seconds=segment_seconds)
        self.best_frame_selector = BestFrameSelector()
        self.sessions: dict[str, dict] = {}

    def ingest_frame(self, session, frame_no: int, frame_time_sec: float, frame, people: list) -> None:
        state = self.sessions.setdefault(session.session_id, self._build_state(session.session_id))
        segment_index = self.window_service.get_segment_index(frame_time_sec)

        if state["current_segment_index"] is None:
            state["current_segment_index"] = segment_index

        if segment_index != state["current_segment_index"]:
            self._flush_current_segment(
                session=session,
                state=state,
                actual_end_sec=frame_time_sec,
                reason="segment_boundary",
            )
            state["current_segment_index"] = segment_index
            state["aggregation"] = self._create_aggregation()

        state["aggregation"].add_frame(
            session_id=session.session_id,
            segment_index=state["current_segment_index"],
            frame_no=frame_no,
            frame_time_sec=frame_time_sec,
            frame=frame,
            people=people,
        )
        state["last_frame_time_sec"] = frame_time_sec

    def finalize_session(self, session, reason: str = "finalize") -> None:
        state = self.sessions.get(session.session_id)
        if not state:
            logger.debug("[Segment] finalize skipped no_state session_id=%s", session.session_id)
            return

        self._flush_current_segment(
            session=session,
            state=state,
            actual_end_sec=state["last_frame_time_sec"],
            reason=reason,
        )
        self._cleanup_state(state)
        self.sessions.pop(session.session_id, None)

    def _flush_current_segment(
        self,
        session,
        state: dict,
        actual_end_sec: float | None,
        reason: str,
    ) -> None:
        segment_index = state["current_segment_index"]
        if segment_index is None:
            return
        if state["last_flushed_segment_index"] == segment_index:
            logger.debug(
                "[Segment] flush skipped already_flushed session_id=%s segment_index=%s reason=%s",
                session.session_id,
                segment_index,
                reason,
            )
            return

        people_results = state["aggregation"].build_people_results()
        representative_frame_path = state["aggregation"].get_representative_frame_path()
        representative_frame_info = state["aggregation"].get_representative_frame_info()
        if not people_results and not representative_frame_path:
            logger.debug(
                "[Segment] flush skipped empty session_id=%s segment_index=%s reason=%s",
                session.session_id,
                segment_index,
                reason,
            )
            return

        segment_start_sec = self.window_service.get_segment_start_sec(segment_index)
        segment_end_sec = self.window_service.get_segment_end_sec(
            segment_index=segment_index,
            actual_end_sec=actual_end_sec,
        )
        logger.info(
            "[Segment] flush session_id=%s segment_index=%s start=%.2f end=%.2f reason=%s",
            session.session_id,
            segment_index,
            segment_start_sec,
            segment_end_sec,
            reason,
        )
        self.persistence_service.save_segment(
            session=session,
            segment_index=segment_index,
            segment_start_sec=segment_start_sec,
            segment_end_sec=segment_end_sec,
            representative_frame_path=representative_frame_path,
            representative_frame_info=representative_frame_info,
            people_results=people_results,
        )
        state["aggregation"].cleanup()
        state["last_flushed_segment_index"] = segment_index

    def _build_state(self, session_id: str) -> dict:
        return {
            "session_id": session_id,
            "current_segment_index": None,
            "last_frame_time_sec": None,
            "last_flushed_segment_index": None,
            "aggregation": self._create_aggregation(),
        }

    def _cleanup_state(self, state: dict) -> None:
        aggregation = state.get("aggregation")
        if aggregation is not None:
            aggregation.cleanup()
        state.clear()

    def _create_aggregation(self) -> SegmentAggregationService:
        return SegmentAggregationService(
            best_frame_selector=self.best_frame_selector,
            file_service=self.file_service,
        )
