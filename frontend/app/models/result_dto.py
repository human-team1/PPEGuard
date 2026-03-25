from dataclasses import dataclass
from typing import Any, Dict

def format_video_time(seconds):
    if seconds is None:
        return "N/A"
    try:
        total_seconds = int(float(seconds))
        minutes = total_seconds // 60
        remain_seconds = total_seconds % 60
        return f"{minutes:02d}:{remain_seconds:02d}"
    except (ValueError, TypeError):
        return "N/A"

def format_datetime_text(value):
    if not value:
        return "-"
    try:
        return str(value).replace("T", " ").split(".")[0]
    except Exception:
        return str(value)

@dataclass
class DetectionResultDto:
    """백엔드 API 원본 응답을 UI에서 안전하게 표시하기 위한 가공 모델(Mapper)"""
    id: str
    session_id: str
    detected_at: str                 # 영상 내 상대 시간
    detected_at_absolute: str        # 실제 발견 시각
    person_index: int
    helmet_status: str
    vest_status: str
    overall_status: str
    ocr_text: str
    image_path: str

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "DetectionResultDto":
        """응답 스키마가 변경되거나 일부 필드가 누락되어도 UI가 깨지지 않게 방어(Fallback) 적용"""
        return cls(
            id=str(data.get("id", "Unknown")),
            session_id=str(data.get("session_id", "Unknown")),
            detected_at=format_video_time(data.get("frame_time_sec")),
            detected_at_absolute=format_datetime_text(data.get("detected_at")),
            person_index=data.get("person_index", 0),
            helmet_status=data.get("helmet_status", "UNKNOWN"),
            vest_status=data.get("vest_status", "UNKNOWN"),
            overall_status=data.get("overall_ppe_status", "UNKNOWN"),
            ocr_text=data.get("ocr_text", "None"),
            image_path=data.get("crop_image_path", "") or data.get("image_path", "")
        )