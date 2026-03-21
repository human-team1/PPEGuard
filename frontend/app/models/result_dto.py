from dataclasses import dataclass
from typing import Any, Dict

@dataclass
class DetectionResultDto:
    """백엔드 API 원본 응답을 UI에서 안전하게 표시하기 위한 가공 모델(Mapper)"""
    id: str
    session_id: str
    detected_at: str
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
            detected_at=data.get("detected_at", "Date N/A"),
            person_index=data.get("person_index", 0),
            helmet_status=data.get("helmet_status", "UNKNOWN"),
            vest_status=data.get("vest_status", "UNKNOWN"),
            overall_status=data.get("overall_ppe_status", "UNKNOWN"),
            ocr_text=data.get("ocr_text", "None"),
            image_path=data.get("image_path", "")
        )
