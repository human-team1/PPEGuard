from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Any


@dataclass
class Person:
    id: int
    bbox: List[int]  # [x1, y1, x2, y2]
    confidence: float

    employee_no: Optional[str] = None
    ocr_confidence: float = 0.0
    ocr_confirmed: bool = False
    last_ocr_at_sec: Optional[float] = None
    ocr_candidate_counts: dict[str, int] = field(default_factory=dict)
    latest_ocr_candidate: Optional[str] = None
    latest_ocr_regex_matched: bool = False
    latest_ocr_raw_text: Optional[str] = None

    has_vest: bool = False
    has_helmet: bool = False
    vest_bbox: Optional[List[int]] = None
    vest_confidence: float = 0.0
    helmet_bbox: Optional[List[int]] = None
    helmet_confidence: float = 0.0

    violation_count: int = 0
    crop_image: Optional[Any] = None
    last_updated: datetime = field(default_factory=datetime.now)

    def is_safe(self) -> bool:
        return self.has_vest and self.has_helmet

    def get_bbox_area(self) -> float:
        x1, y1, x2, y2 = self.bbox
        return (x2 - x1) * (y2 - y1)
