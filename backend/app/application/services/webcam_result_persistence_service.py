from datetime import datetime, timedelta
from decimal import Decimal

from app.domain.entities.analysis_frame import AnalysisFrame, FrameProcessingStatus
from app.domain.entities.analysis_track_summary import AnalysisTrackSummary
from app.domain.entities.detection_result import DetectionResult, ItemWearStatus
from app.domain.rules.ppe_validation import get_overall_ppe_status


class WebcamResultPersistenceService:
    def __init__(self, frame_repo, detection_result_repo, track_summary_repo, file_service):
        self.frame_repo = frame_repo
        self.detection_result_repo = detection_result_repo
        self.track_summary_repo = track_summary_repo
        self.file_service = file_service

    def persist_frame_event(
        self,
        session,
        frame_no: int,
        frame_time_sec: float,
        frame,
        people: list,
        track_states: dict[int, object],
        reason: str,
    ):
        if not people or frame is None or session.id is None:
            return None

        now = datetime.now()
        frame_path = self.file_service.save_webcam_frame(session.session_id, frame_no, frame)
        analysis_frame = AnalysisFrame(
            session_id=session.id,
            frame_no=frame_no,
            frame_time_sec=Decimal(str(round(frame_time_sec, 2))),
            person_count=len(people),
            processing_status=FrameProcessingStatus.PROCESSED,
            captured_at=self._resolve_captured_at(session, frame_time_sec, now),
            frame_image_path=frame_path,
            frame_width=int(frame.shape[1]) if getattr(frame, "shape", None) is not None else None,
            frame_height=int(frame.shape[0]) if getattr(frame, "shape", None) is not None else None,
            created_at=now,
            updated_at=now,
        )
        self.frame_repo.save(analysis_frame)

        for person in people:
            track_state = track_states.get(person.id)
            result = DetectionResult(
                frame_id=analysis_frame.id,
                person_index=person.id,
                track_id=person.id,
                employee_no=getattr(track_state, "employee_no", None) or getattr(person, "employee_no", None),
                ocr_text=getattr(track_state, "latest_ocr_text", None) or getattr(person, "latest_ocr_raw_text", None),
                ocr_confidence=self._to_decimal(getattr(track_state, "latest_ocr_confidence", None) or getattr(person, "ocr_confidence", None)),
                overall_ppe_status=get_overall_ppe_status(
                    ItemWearStatus.WEARING if getattr(person, "has_helmet", False) else ItemWearStatus.NOT_WEARING,
                    ItemWearStatus.WEARING if getattr(person, "has_vest", False) else ItemWearStatus.NOT_WEARING,
                ),
                helmet_status=ItemWearStatus.WEARING if getattr(person, "has_helmet", False) else ItemWearStatus.NOT_WEARING,
                vest_status=ItemWearStatus.WEARING if getattr(person, "has_vest", False) else ItemWearStatus.NOT_WEARING,
                person_box_x=int(person.bbox[0]),
                person_box_y=int(person.bbox[1]),
                person_box_width=max(int(person.bbox[2]) - int(person.bbox[0]), 0),
                person_box_height=max(int(person.bbox[3]) - int(person.bbox[1]), 0),
                created_at=now,
                updated_at=now,
            )
            self.detection_result_repo.save(result)
            self._upsert_track_summary(
                session=session,
                track_state=track_state,
                frame=analysis_frame,
                frame_path=frame_path,
                fallback_person=person,
            )
        return analysis_frame

    def flush_track_summary(self, session, track_state, frame=None, frame_no: int | None = None, frame_time_sec: float | None = None):
        if session.id is None or track_state is None:
            return None

        frame_record = None
        frame_path = getattr(track_state, "best_image_path", None)
        if frame is not None and frame_no is not None and frame_time_sec is not None:
            frame_path = self.file_service.save_webcam_frame(session.session_id, frame_no, frame)
            now = datetime.now()
            frame_record = AnalysisFrame(
                session_id=session.id,
                frame_no=frame_no,
                frame_time_sec=Decimal(str(round(frame_time_sec, 2))),
                person_count=1,
                processing_status=FrameProcessingStatus.PROCESSED,
                captured_at=self._resolve_captured_at(session, frame_time_sec, now),
                frame_image_path=frame_path,
                frame_width=int(frame.shape[1]) if getattr(frame, "shape", None) is not None else None,
                frame_height=int(frame.shape[0]) if getattr(frame, "shape", None) is not None else None,
                created_at=now,
                updated_at=now,
            )
            self.frame_repo.save(frame_record)

        return self._upsert_track_summary(
            session=session,
            track_state=track_state,
            frame=frame_record,
            frame_path=frame_path,
            fallback_person=None,
        )

    def _upsert_track_summary(self, session, track_state, frame, frame_path: str | None, fallback_person):
        if track_state is None:
            return None

        now = datetime.now()
        snapshot = getattr(track_state, "last_snapshot", {}) or {}
        existing = self.track_summary_repo.find_by_session_and_track_id(session.id, track_state.track_id)
        summary = existing or AnalysisTrackSummary(
            session_id=session.id,
            track_id=track_state.track_id,
            overall_ppe_status="UNKNOWN",
            helmet_status="UNKNOWN",
            vest_status="UNKNOWN",
            created_at=now,
            updated_at=now,
        )
        is_best_frame = bool(
            frame is not None
            and getattr(track_state, "best_frame_frame_no", None) == getattr(frame, "frame_no", None)
        )
        if summary.representative_frame_id is None and frame is not None:
            summary.representative_frame_id = frame.id
        elif is_best_frame and frame is not None:
            summary.representative_frame_id = frame.id
        summary.employee_no = track_state.employee_no or summary.employee_no
        summary.latest_ocr_text = track_state.latest_ocr_text or summary.latest_ocr_text
        summary.latest_ocr_confidence = self._to_decimal(track_state.latest_ocr_confidence) or summary.latest_ocr_confidence
        summary.ocr_confirmed = bool(track_state.ocr_confirmed)
        summary.helmet_status = snapshot.get("helmet_status") or summary.helmet_status
        summary.vest_status = snapshot.get("vest_status") or summary.vest_status
        summary.overall_ppe_status = self._resolve_overall_status(summary.helmet_status, summary.vest_status)
        summary.violation_count = max(int(getattr(track_state, "violation_count", 0) or 0), summary.violation_count)
        summary.first_seen_frame_no = getattr(track_state, "first_seen_frame_no", None) or summary.first_seen_frame_no
        summary.last_seen_frame_no = getattr(track_state, "last_seen_frame_no", None) or summary.last_seen_frame_no
        summary.first_seen_at_sec = self._to_decimal(getattr(track_state, "first_seen_at", None)) or summary.first_seen_at_sec
        summary.last_seen_at_sec = self._to_decimal(getattr(track_state, "last_seen_at", None)) or summary.last_seen_at_sec
        if summary.best_image_path is None and frame_path:
            summary.best_image_path = frame_path
        elif is_best_frame and frame_path:
            summary.best_image_path = frame_path
        summary.updated_at = now
        self.track_summary_repo.upsert(summary)
        if is_best_frame and frame_path:
            track_state.best_image_path = frame_path
        return summary

    @staticmethod
    def _resolve_overall_status(helmet_status: str, vest_status: str) -> str:
        if helmet_status == "NOT_WORN" or vest_status == "NOT_WORN":
            return "NON_COMPLIANT"
        if helmet_status == "WORN" and vest_status == "WORN":
            return "COMPLIANT"
        return "UNKNOWN"

    @staticmethod
    def _resolve_captured_at(session, frame_time_sec: float, fallback_now: datetime):
        if getattr(session, "started_at", None):
            return session.started_at + timedelta(seconds=float(frame_time_sec or 0.0))
        return fallback_now

    @staticmethod
    def _to_decimal(value):
        if value is None:
            return None
        return Decimal(str(round(float(value), 4)))
