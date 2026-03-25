import base64
import dataclasses
from datetime import datetime
from decimal import Decimal
from enum import Enum

import cv2

from app import socketio


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

    def emit_progress(
        self,
        session_id: str,
        source_type: str,
        current_time_sec: float,
        total_time_sec: float,
        processed_frames: int,
        current_counts: dict,
    ):
        progress_percent = 0.0
        if total_time_sec > 0:
            progress_percent = min(100.0, (current_time_sec / total_time_sec) * 100.0)

        socketio.emit(
            "analysis_progress",
            self._to_jsonable(
                {
                    "session_id": session_id,
                    "source_type": source_type,
                    "current_time_sec": current_time_sec,
                    "total_time_sec": total_time_sec,
                    "progress_percent": progress_percent,
                    "processed_frames": processed_frames,
                    "current_counts": current_counts,
                }
            ),
        )

    def emit_frame_result(
        self,
        session_id: str,
        source_type: str,
        frame,
        detections: list[dict],
    ):
        preview_frame, width, height = self._encode_preview_frame(frame)
        socketio.emit(
            "analysis_frame_result",
            self._to_jsonable(
                {
                    "session_id": session_id,
                    "source_type": source_type,
                    "preview_frame": preview_frame,
                    "frame_width": width,
                    "frame_height": height,
                    "detections": detections,
                }
            ),
        )

    def emit_segment_saved(
        self,
        session_id: str,
        segment_index: int,
        segment_start_sec: float,
        segment_end_sec: float,
        best_frame_path: str | None,
        detected_person_count: int,
        confirmed_ocr_person_count: int,
        person_results: list[dict],
    ):
        print(
            "[Realtime] emit analysis_segment_saved - "
            f"session_id={session_id}, segment_index={segment_index}, "
            f"people={len(person_results)}, confirmed={confirmed_ocr_person_count}",
            flush=True,
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
                    "detected_person_count": detected_person_count,
                    "confirmed_ocr_person_count": confirmed_ocr_person_count,
                    "person_results": person_results,
                }
            ),
        )

    def _encode_preview_frame(self, frame):
        if frame is None or getattr(frame, "size", 0) == 0:
            return None, 0, 0

        preview = frame.copy()
        height, width = preview.shape[:2]
        if width > self.preview_width:
            aspect_ratio = height / width
            preview = cv2.resize(
                preview,
                (self.preview_width, int(self.preview_width * aspect_ratio)),
            )
            height, width = preview.shape[:2]

        success, buffer = cv2.imencode(
            ".jpg",
            preview,
            [cv2.IMWRITE_JPEG_QUALITY, 65],
        )
        if not success:
            return None, width, height

        return base64.b64encode(buffer).decode("utf-8"), width, height

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
