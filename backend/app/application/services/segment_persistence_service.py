import logging
from datetime import timedelta

from app.domain.entities.analysis_session import AnalysisSourceType
from app.domain.entities.analysis_segment import AnalysisSegmentPersonResult, AnalysisSegmentSummary


logger = logging.getLogger(__name__)


class SegmentPersistenceService:
    def __init__(self, segment_summary_repo, segment_person_result_repo, realtime_event_service=None):
        self.segment_summary_repo = segment_summary_repo
        self.segment_person_result_repo = segment_person_result_repo
        self.realtime_event_service = realtime_event_service

    def save_segment(
        self,
        session,
        segment_index: int,
        segment_start_sec: float,
        segment_end_sec: float,
        representative_frame_path: str | None,
        representative_frame_info: dict | None,
        people_results: list[dict],
    ):
        if not people_results and not representative_frame_path:
            return None

        reference_time = None
        if session.video_started_at is not None:
            reference_time = session.video_started_at + timedelta(seconds=segment_end_sec)

        summary = AnalysisSegmentSummary(
            session_id=session.id,
            segment_index=segment_index,
            segment_start_sec=segment_start_sec,
            segment_end_sec=segment_end_sec,
            representative_frame_path=representative_frame_path,
            person_count=len(people_results),
            confirmed_person_count=sum(1 for person in people_results if person["ocr_confirmed"]),
            reference_time=reference_time,
        )
        self.segment_summary_repo.save(summary)
        logger.info(
            "[DB] segment summary saved session_id=%s segment_id=%s segment_index=%s person_count=%s confirmed_count=%s",
            session.session_id,
            summary.id,
            segment_index,
            summary.person_count,
            summary.confirmed_person_count,
        )

        person_results = [
            AnalysisSegmentPersonResult(
                segment_summary_id=summary.id,
                track_id=person["track_id"],
                employee_id=person["employee_id"],
                ocr_number=person["ocr_number"],
                ocr_confirmed=person["ocr_confirmed"],
                helmet_status=person["helmet_status"],
                vest_status=person["vest_status"],
                observed_frames=person["observed_frames"],
                helmet_detected_frames=person["helmet_detected_frames"],
                vest_detected_frames=person["vest_detected_frames"],
                regex_match_count=person["regex_match_count"],
            )
            for person in people_results
        ]
        self.segment_person_result_repo.save_many(person_results)
        logger.info(
            "[DB] segment person results saved session_id=%s segment_id=%s count=%s",
            session.session_id,
            summary.id,
            len(person_results),
        )
        if self.realtime_event_service and session.source_type == AnalysisSourceType.WEBCAM:
            self.realtime_event_service.emit_segment_saved(
                session_id=session.session_id,
                segment_index=segment_index,
                segment_start_sec=segment_start_sec,
                segment_end_sec=segment_end_sec,
                best_frame_path=representative_frame_path,
                representative_frame=representative_frame_info,
                detected_person_count=summary.person_count,
                confirmed_ocr_person_count=summary.confirmed_person_count,
                person_results=people_results,
            )
        return summary
