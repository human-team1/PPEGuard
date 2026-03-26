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
    best_bbox: tuple[int, int, int, int] | None = None


class SegmentAggregationService:
    def __init__(self, best_frame_selector, file_service, active_inspection_items: set[str] | None = None):
        self.best_frame_selector = best_frame_selector
        self.file_service = file_service
        self.active_inspection_items = active_inspection_items or {"helmet", "vest"}
        self.people: dict[int, SegmentPersonAggregate] = {}
        self.best_frame: dict | None = None
        self.frame_candidates: list[dict] = []

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
        ocr_visible_person_count = 0
        ocr_visible_violation_person_count = 0
        identified_violation_person_count = 0
        confirmed_violation_person_count = 0
        ocr_confidences = []
        confirmed_ocr_person_count = 0
        violation_person_count = 0
        selected_violation_person_count = 0
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
            if bbox_area >= aggregate.best_bbox_area:
                aggregate.best_bbox = (
                    int(person.bbox[0]),
                    int(person.bbox[1]),
                    int(person.bbox[2]),
                    int(person.bbox[3]),
                )
            max_bbox_area = max(max_bbox_area, bbox_area)

            if getattr(person, "has_helmet", False):
                aggregate.helmet_detected_frames += 1
            if getattr(person, "has_vest", False):
                aggregate.vest_detected_frames += 1
            selected_violation_types = self._resolve_selected_violation_types(person)
            if not person.is_safe():
                violation_person_count += 1
            if selected_violation_types:
                selected_violation_person_count += 1

            candidate = getattr(person, "latest_ocr_candidate", None)
            regex_matched = bool(getattr(person, "latest_ocr_regex_matched", False))
            confidence = float(getattr(person, "ocr_confidence", 0.0) or 0.0)
            identified_employee_no = getattr(person, "employee_no", None)

            if candidate:
                ocr_visible_person_count += 1
                if selected_violation_types:
                    ocr_visible_violation_person_count += 1
            if selected_violation_types and identified_employee_no:
                identified_violation_person_count += 1
            if selected_violation_types and bool(getattr(person, "ocr_confirmed", False)) and identified_employee_no:
                confirmed_violation_person_count += 1

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
                    "selected_violation_types": list(selected_violation_types),
                }
            )

        avg_ocr_confidence = sum(ocr_confidences) / len(ocr_confidences) if ocr_confidences else 0.0
        selection_reason = self._resolve_selection_reason(
            confirmed_violation_person_count=confirmed_violation_person_count,
            confirmed_ocr_person_count=confirmed_ocr_person_count,
            violation_person_count=selected_violation_person_count,
            ocr_visible_person_count=ocr_visible_person_count,
            max_bbox_area=max_bbox_area,
        )
        candidate_frame = {
            "frame_no": frame_no,
            "frame_time_sec": frame_time_sec,
            "regex_match_count": regex_match_count,
            "ocr_visible_person_count": ocr_visible_person_count,
            "ocr_visible_violation_person_count": ocr_visible_violation_person_count,
            "identified_violation_person_count": identified_violation_person_count,
            "confirmed_violation_person_count": confirmed_violation_person_count,
            "person_count": len(people),
            "avg_ocr_confidence": avg_ocr_confidence,
            "confirmed_ocr_person_count": confirmed_ocr_person_count,
            "violation_person_count": selected_violation_person_count,
            "raw_violation_person_count": violation_person_count,
            "max_bbox_area": max_bbox_area,
            "selection_reason": selection_reason,
            "detections": detections,
        }

        if selected_violation_person_count <= 0:
            return

        self.frame_candidates.append(
            {
                **candidate_frame,
                "session_id": session_id,
                "segment_index": segment_index,
                "frame_image": frame.copy() if hasattr(frame, "copy") else frame,
            }
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
                    "bbox": self._build_bbox_dict(aggregate.best_bbox),
                }
            )

        ordered_results = sorted(results, key=lambda item: item["local_person_id"])
        self._finalize_best_frame(ordered_results)
        return ordered_results

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
        for candidate in self.frame_candidates:
            candidate.pop("frame_image", None)
            candidate.clear()
        self.frame_candidates.clear()
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
        confirmed_violation_person_count: int,
        confirmed_ocr_person_count: int,
        violation_person_count: int,
        ocr_visible_person_count: int,
        max_bbox_area: float,
    ) -> str:
        if confirmed_violation_person_count > 0:
            return "confirmed_violation"
        if violation_person_count > 0:
            return "ppe_violation"
        if ocr_visible_person_count > 0:
            return "ocr_visible"
        if confirmed_ocr_person_count > 0:
            return "ocr_confirmed"
        if max_bbox_area > 0:
            return "best_bbox"
        return "person_detected"

    def _resolve_selected_violation_types(self, person) -> list[str]:
        violation_types: list[str] = []
        if "helmet" in self.active_inspection_items and not getattr(person, "has_helmet", False):
            violation_types.append("helmet_missing")
        if "vest" in self.active_inspection_items and not getattr(person, "has_vest", False):
            violation_types.append("vest_missing")
        return violation_types

    def _finalize_best_frame(self, people_results: list[dict]) -> None:
        if self.best_frame is not None or not self.frame_candidates:
            return

        confirmed_violation_ids = {
            int(person["local_person_id"])
            for person in people_results
            if person.get("ocr_confirmed") and self._is_selected_violation_result(person)
        }
        candidate_frame_nos = [candidate.get("frame_no") for candidate in self.frame_candidates]
        logger.info(
            "[Segment] finalize best frame start confirmed_violation_ids=%s candidate_frame_nos=%s",
            sorted(confirmed_violation_ids),
            candidate_frame_nos,
        )
        if not confirmed_violation_ids:
            logger.info(
                "[Segment] finalize best frame skipped confirmed_violation_ids=[] candidate_frame_nos=%s",
                candidate_frame_nos,
            )
            return

        best_candidate = None
        for candidate in self.frame_candidates:
            confirmed_violation_person_count = sum(
                1
                for detection in candidate.get("detections", [])
                if detection.get("local_person_id") in confirmed_violation_ids
                and detection.get("selected_violation_types")
            )
            if confirmed_violation_person_count <= 0:
                continue

            finalized_candidate = {
                **candidate,
                "confirmed_violation_person_count": confirmed_violation_person_count,
            }
            if self.best_frame_selector.is_better(finalized_candidate, best_candidate):
                best_candidate = finalized_candidate

        if best_candidate is None:
            logger.info(
                "[Segment] finalize best frame no_match confirmed_violation_ids=%s candidate_frame_nos=%s",
                sorted(confirmed_violation_ids),
                candidate_frame_nos,
            )
            return

        saved_path = self.file_service.save_segment_frame(
            session_id=best_candidate["session_id"],
            segment_index=best_candidate["segment_index"],
            frame_no=best_candidate["frame_no"],
            frame_image=best_candidate.get("frame_image"),
        )
        if not saved_path:
            return

        self.best_frame = {k: v for k, v in best_candidate.items() if k != "frame_image"}
        self.best_frame["path"] = saved_path
        selected_detection_ids = [
            detection.get("local_person_id")
            for detection in best_candidate.get("detections", [])
        ]
        logger.info(
            "[Segment] finalize best frame selected frame_no=%s detection_local_person_ids=%s confirmed_violation_ids=%s",
            best_candidate["frame_no"],
            selected_detection_ids,
            sorted(confirmed_violation_ids),
        )
        logger.debug(
            "[Segment] best frame finalized session_id=%s segment_index=%s frame_no=%s confirmed_violation_count=%s",
            best_candidate["session_id"],
            best_candidate["segment_index"],
            best_candidate["frame_no"],
            best_candidate["confirmed_violation_person_count"],
        )

    def _is_selected_violation_result(self, person: dict) -> bool:
        if "helmet" in self.active_inspection_items and person.get("helmet_status") == SegmentWearStatus.NOT_WORN:
            return True
        if "vest" in self.active_inspection_items and person.get("vest_status") == SegmentWearStatus.NOT_WORN:
            return True
        return False

    @staticmethod
    def _build_bbox_dict(bbox: tuple[int, int, int, int] | None) -> dict | None:
        if bbox is None:
            return None
        x1, y1, x2, y2 = bbox
        return {
            "x1": int(x1),
            "y1": int(y1),
            "x2": int(x2),
            "y2": int(y2),
        }
