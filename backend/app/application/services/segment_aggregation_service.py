import logging
from dataclasses import dataclass, field
from typing import Optional

from app.domain.entities.analysis_segment import SegmentWearStatus


logger = logging.getLogger(__name__)


@dataclass
class SegmentPersonAggregate:
    local_person_id: int
    employee_id: Optional[str] = None
    ocr_number: Optional[str] = None
    ocr_confirmed: bool = False
    observed_frames: int = 0
    helmet_detected_frames: int = 0
    vest_detected_frames: int = 0
    regex_match_count: int = 0
    ocr_candidate_counts: dict[str, int] = field(default_factory=dict)
    best_bbox_area: float = 0.0


class SegmentAggregationService:
    def __init__(self, best_frame_selector, file_service):
        self.best_frame_selector = best_frame_selector
        self.file_service = file_service
        self.people: dict[int, SegmentPersonAggregate] = {}
        self.best_frame: dict | None = None

    def add_frame(
        self,
        session_id: str,
        segment_index: int,
        frame_no: int,
        frame_time_sec: float,
        frame,
        people: list,
    ) -> None:
        regex_match_count = 0
        ocr_confidences = []
        confirmed_ocr_person_count = 0
        violation_person_count = 0
        max_bbox_area = 0.0
        detections = []

        for person in people:
            aggregate = self.people.setdefault(
                person.id,
                SegmentPersonAggregate(local_person_id=person.id),
            )
            aggregate.observed_frames += 1
            bbox_area = float(person.get_bbox_area()) if hasattr(person, "get_bbox_area") else 0.0
            aggregate.best_bbox_area = max(aggregate.best_bbox_area, bbox_area)
            max_bbox_area = max(max_bbox_area, bbox_area)

            if getattr(person, "has_helmet", False):
                aggregate.helmet_detected_frames += 1
            if getattr(person, "has_vest", False):
                aggregate.vest_detected_frames += 1
            if not person.is_safe():
                violation_person_count += 1

            candidate = getattr(person, "latest_ocr_candidate", None)
            regex_matched = bool(getattr(person, "latest_ocr_regex_matched", False))
            confidence = float(getattr(person, "ocr_confidence", 0.0) or 0.0)

            if candidate and regex_matched:
                aggregate.ocr_candidate_counts[candidate] = (
                    aggregate.ocr_candidate_counts.get(candidate, 0) + 1
                )
                aggregate.regex_match_count += 1
                regex_match_count += 1
                ocr_confidences.append(confidence)

                if aggregate.ocr_candidate_counts[candidate] >= 2:
                    aggregate.ocr_confirmed = True
                    aggregate.ocr_number = candidate
                    aggregate.employee_id = candidate

            if not aggregate.ocr_confirmed and getattr(person, "employee_no", None):
                aggregate.ocr_confirmed = bool(getattr(person, "ocr_confirmed", False))
                aggregate.ocr_number = person.employee_no
                aggregate.employee_id = person.employee_no
            if aggregate.ocr_confirmed:
                confirmed_ocr_person_count += 1

            detections.append(
                {
                    "local_person_id": person.id,
                    "track_id": person.id,
                    "employee_id": getattr(person, "employee_no", None),
                    "helmet_status": "WORN" if getattr(person, "has_helmet", False) else "NOT_WORN",
                    "vest_status": "WORN" if getattr(person, "has_vest", False) else "NOT_WORN",
                    "bbox": {
                        "x1": int(person.bbox[0]),
                        "y1": int(person.bbox[1]),
                        "x2": int(person.bbox[2]),
                        "y2": int(person.bbox[3]),
                    },
                }
            )

        avg_ocr_confidence = sum(ocr_confidences) / len(ocr_confidences) if ocr_confidences else 0.0
        selection_reason = self._resolve_selection_reason(
            confirmed_ocr_person_count=confirmed_ocr_person_count,
            violation_person_count=violation_person_count,
            max_bbox_area=max_bbox_area,
        )
        candidate_frame = {
            "frame_no": frame_no,
            "frame_time_sec": frame_time_sec,
            "regex_match_count": regex_match_count,
            "person_count": len(people),
            "avg_ocr_confidence": avg_ocr_confidence,
            "confirmed_ocr_person_count": confirmed_ocr_person_count,
            "violation_person_count": violation_person_count,
            "max_bbox_area": max_bbox_area,
            "selection_reason": selection_reason,
            "detections": detections,
        }

        if self.best_frame_selector.is_better(candidate_frame, self.best_frame):
            saved_path = self.file_service.save_segment_frame(
                session_id=session_id,
                segment_index=segment_index,
                frame_no=frame_no,
                frame_image=frame,
            )
            if saved_path:
                previous_path = None if self.best_frame is None else self.best_frame.get("path")
                self.best_frame = {**candidate_frame, "path": saved_path}
                self.file_service.delete_file(previous_path)
                logger.debug(
                    "[Segment] best frame updated session_id=%s segment_index=%s frame_no=%s",
                    session_id,
                    segment_index,
                    frame_no,
                )

    def build_people_results(self) -> list[dict]:
        results = []
        for aggregate in self.people.values():
            results.append(
                {
                    "local_person_id": aggregate.local_person_id,
                    "track_id": aggregate.local_person_id,
                    "employee_id": aggregate.employee_id,
                    "ocr_number": aggregate.ocr_number,
                    "ocr_confirmed": aggregate.ocr_confirmed,
                    "helmet_status": self._get_segment_wear_status(
                        aggregate.helmet_detected_frames,
                        aggregate.observed_frames,
                    ),
                    "vest_status": self._get_segment_wear_status(
                        aggregate.vest_detected_frames,
                        aggregate.observed_frames,
                    ),
                    "observed_frames": aggregate.observed_frames,
                    "helmet_detected_frames": aggregate.helmet_detected_frames,
                    "vest_detected_frames": aggregate.vest_detected_frames,
                    "regex_match_count": aggregate.regex_match_count,
                }
            )

        return sorted(results, key=lambda item: item["local_person_id"])

    def get_representative_frame_path(self) -> Optional[str]:
        if self.best_frame is None:
            return None
        return self.best_frame.get("path")

    def get_representative_frame_info(self) -> Optional[dict]:
        if self.best_frame is None:
            return None
        return dict(self.best_frame)

    def cleanup(self) -> None:
        self.people.clear()
        if self.best_frame is not None:
            self.best_frame.clear()
        self.best_frame = None

    def _get_segment_wear_status(self, detected_frames: int, observed_frames: int) -> SegmentWearStatus:
        if observed_frames <= 0:
            return SegmentWearStatus.UNKNOWN
        if (detected_frames / observed_frames) >= 0.5:
            return SegmentWearStatus.WORN
        return SegmentWearStatus.NOT_WORN

    def _resolve_selection_reason(
        self,
        confirmed_ocr_person_count: int,
        violation_person_count: int,
        max_bbox_area: float,
    ) -> str:
        if confirmed_ocr_person_count > 0:
            return "ocr_confirmed"
        if violation_person_count > 0:
            return "ppe_violation"
        if max_bbox_area > 0:
            return "best_bbox"
        return "person_detected"
