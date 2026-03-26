import dataclasses
import logging
from datetime import datetime
from decimal import Decimal
from enum import Enum

from app import socketio


logger = logging.getLogger(__name__)


class RealtimeEventService:
    def __init__(self, preview_width: int = 640, min_emit_interval_sec: float = 1.0):
        self.preview_width = preview_width
        self.min_emit_interval_sec = min_emit_interval_sec

    def emit_session_status(self, session_id: str, source_type: str, status: str):
        socketio.emit(
            "analysis_session_status",
            self._to_jsonable(
                {
                    "session_id": session_id,
                    "source_type": source_type,
                    "status": status,
                }
            ),
        )

    def emit_error(self, message: str):
        logger.error("[Realtime] error emitted message=%s", message)
        socketio.emit(
            "error",
            self._to_jsonable({"message": message}),
        )

    def emit_progress(
        self,
        session_id: str,
        source_type: str,
        current_time_sec: float,
        total_time_sec: float,
        processed_frames: int,
        current_counts: dict,
        active_person_count: int = 0,
        violating_person_count: int = 0,
        violation_rate: float = 0.0,
        track_summaries: list[dict] | None = None,
    ):
        progress_percent = 0.0
        if total_time_sec > 0:
            progress_percent = min(100.0, (current_time_sec / total_time_sec) * 100.0)

        payload = {
            "session_id": session_id,
            "source_type": source_type,
            "current_time_sec": current_time_sec,
            "total_time_sec": total_time_sec,
            "progress_percent": progress_percent,
            "processed_frames": processed_frames,
            "active_person_count": active_person_count,
            "violating_person_count": violating_person_count,
            "violation_rate": violation_rate,
            "current_counts": current_counts,
            "track_summaries": track_summaries or [],
        }
        logger.debug(
            "[Realtime] progress emitted session_id=%s source=%s processed_frames=%s track_count=%s",
            session_id,
            source_type,
            processed_frames,
            len(track_summaries or []),
        )

        socketio.emit(
            "analysis_progress",
            self._to_jsonable(payload),
        )

    def emit_frame_result(
        self,
        session_id: str,
        source_type: str,
        processed_frames: int,
        tracks_count: int,
        violations_count: int,
        frame_no: int | None,
        frame_time_sec: float | None,
        frame_width: int,
        frame_height: int,
        detections: list[dict],
    ):
        payload = {
            "session_id": session_id,
            "source_type": source_type,
            "status": "processing",
            "processed_frames": processed_frames,
            "tracks_count": tracks_count,
            "violations_count": violations_count,
            "frame_no": frame_no,
            "frame_time_sec": frame_time_sec,
            "frame_width": frame_width,
            "frame_height": frame_height,
            "detections": detections,
        }
        logger.info(
            "[Realtime] frame_result emitted session_id=%s frame_no=%s processed_frames=%s tracks_count=%s detections_count=%s violations_count=%s image_len=%s",
            session_id,
            frame_no,
            processed_frames,
            tracks_count,
            len(detections or []),
            violations_count,
            0,
        )
        socketio.emit(
            "analysis_frame_result",
            self._to_jsonable(payload),
        )

    def emit_segment_saved(
        self,
        session_id: str,
        segment_index: int,
        segment_start_sec: float,
        segment_end_sec: float,
        best_frame_path: str | None,
        representative_frame: dict | None,
        detected_person_count: int,
        confirmed_ocr_person_count: int,
        person_results: list[dict],
    ):
        logger.info(
            "[Segment] saved session_id=%s segment_index=%s people=%s confirmed=%s",
            session_id,
            segment_index,
            len(person_results),
            confirmed_ocr_person_count,
        )
        socketio.emit(
            "analysis_segment_saved",
            self._to_jsonable(
                {
                    "session_id": session_id,
                    "segment_index": segment_index,
                    "segment_start_sec": segment_start_sec,
                    "segment_end_sec": segment_end_sec,
                    "best_frame_path": best_frame_path,
                    "representative_frame": representative_frame,
                    "detected_person_count": detected_person_count,
                    "confirmed_ocr_person_count": confirmed_ocr_person_count,
                    "person_results": person_results,
                }
            ),
        )

    def emit_webcam_track_confirmed(
        self,
        session_id: str,
        source_type: str,
        track_id: int,
        employee_id: str,
        confirmed_at_sec: float,
        bbox: dict,
    ):
        logger.info(
            "[OCR] confirmed track_id=%s employee_no=%s session_id=%s",
            track_id,
            employee_id,
            session_id,
        )
        socketio.emit(
            "analysis_track_confirmed",
            self._to_jsonable(
                {
                    "session_id": session_id,
                    "source_type": source_type,
                    "track_id": track_id,
                    "employee_id": employee_id,
                    "confirmed_at_sec": confirmed_at_sec,
                    "bbox": bbox,
                }
            ),
        )

    def _to_jsonable(self, obj):
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if dataclasses.is_dataclass(obj):
            return self._to_jsonable(dataclasses.asdict(obj))
        if isinstance(obj, dict):
            return {str(key): self._to_jsonable(value) for key, value in obj.items()}
        if isinstance(obj, (list, tuple, set)):
            return [self._to_jsonable(item) for item in obj]
        return str(obj)
