from app.application.dtos import (
    AnalysisSegmentListResponseDto,
    AnalysisSegmentPersonResultResponseDto,
    AnalysisSegmentSummaryResponseDto,
)


class GetSessionSegmentsUseCase:
    def __init__(self, session_repo, segment_summary_repo, segment_person_result_repo):
        self.session_repo = session_repo
        self.segment_summary_repo = segment_summary_repo
        self.segment_person_result_repo = segment_person_result_repo

    def execute(self, session_id: str):
        session = self.session_repo.find_by_session_id(session_id)
        if session is None or session.id is None:
            raise ValueError("Analysis session not found")

        summaries = self.segment_summary_repo.find_by_session_id(session.id)
        people_map = self.segment_person_result_repo.find_by_segment_summary_ids(
            [summary.id for summary in summaries if summary.id is not None]
        )

        return AnalysisSegmentListResponseDto(
            session_id=session.session_id,
            segments=[
                AnalysisSegmentSummaryResponseDto(
                    segment_id=summary.id,
                    segment_index=summary.segment_index,
                    segment_start_sec=summary.segment_start_sec,
                    segment_end_sec=summary.segment_end_sec,
                    representative_frame_path=summary.representative_frame_path,
                    person_count=summary.person_count,
                    confirmed_person_count=summary.confirmed_person_count,
                    reference_time=summary.reference_time,
                    created_at=summary.created_at,
                    updated_at=summary.updated_at,
                    people=[
                        AnalysisSegmentPersonResultResponseDto(
                            person_result_id=person.id,
                            local_person_id=person.track_id,
                            track_id=person.track_id,
                            employee_id=person.employee_id,
                            ocr_number=person.ocr_number,
                            ocr_confirmed=person.ocr_confirmed,
                            helmet_status=person.helmet_status.value,
                            vest_status=person.vest_status.value,
                            observed_frames=person.observed_frames,
                            helmet_detected_frames=person.helmet_detected_frames,
                            vest_detected_frames=person.vest_detected_frames,
                            regex_match_count=person.regex_match_count,
                            created_at=person.created_at,
                            updated_at=person.updated_at,
                        )
                        for person in people_map.get(summary.id, [])
                    ],
                )
                for summary in summaries
            ],
        )
