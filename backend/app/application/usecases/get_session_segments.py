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
        final_status_map = self._build_session_final_status_map(people_map)

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
                            session_final_helmet_status=self._resolve_final_item_status(
                                final_status_map,
                                person,
                                "helmet_status",
                            ),
                            session_final_vest_status=self._resolve_final_item_status(
                                final_status_map,
                                person,
                                "vest_status",
                            ),
                            observed_frames=person.observed_frames,
                            helmet_detected_frames=person.helmet_detected_frames,
                            vest_detected_frames=person.vest_detected_frames,
                            regex_match_count=person.regex_match_count,
                            bbox_x1=person.bbox_x1,
                            bbox_y1=person.bbox_y1,
                            bbox_x2=person.bbox_x2,
                            bbox_y2=person.bbox_y2,
                            created_at=person.created_at,
                            updated_at=person.updated_at,
                        )
                        for person in people_map.get(summary.id, [])
                    ],
                )
                for summary in summaries
            ],
        )

    def _build_session_final_status_map(self, people_map: dict[int, list]):
        final_status_map: dict[str, dict[str, list[str]]] = {}

        for people in people_map.values():
            for person in people:
                person_key = self._resolve_person_key(person)
                if not person_key:
                    continue

                status_bucket = final_status_map.setdefault(
                    person_key,
                    {
                        "helmet_status": [],
                        "vest_status": [],
                    },
                )
                status_bucket["helmet_status"].append(person.helmet_status.value)
                status_bucket["vest_status"].append(person.vest_status.value)

        return final_status_map

    def _resolve_final_item_status(self, final_status_map: dict, person, field_name: str):
        person_key = self._resolve_person_key(person)
        if not person_key:
            return getattr(person, field_name).value

        status_bucket = final_status_map.get(person_key, {})
        statuses = status_bucket.get(field_name, [])
        return self._merge_session_statuses(statuses, getattr(person, field_name).value)

    @staticmethod
    def _resolve_person_key(person) -> str | None:
        employee_id = getattr(person, "employee_id", None)
        ocr_number = getattr(person, "ocr_number", None)
        identifier = employee_id or ocr_number
        if not identifier:
            return None
        return str(identifier).strip()

    @staticmethod
    def _merge_session_statuses(statuses: list[str], fallback_status: str) -> str:
        normalized = [str(status).strip().upper() for status in statuses if status]
        if "WORN" in normalized:
            return "WORN"
        if normalized:
            if "NOT_WORN" in normalized:
                return "NOT_WORN"
            if "UNKNOWN" in normalized:
                return "UNKNOWN"
        return fallback_status
