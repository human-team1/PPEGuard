from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class AnalysisTrackSummary:
    session_id: int
    track_id: int
    overall_ppe_status: str
    helmet_status: str
    vest_status: str

    id: Optional[int] = None
    representative_frame_id: Optional[int] = None
    employee_no: Optional[str] = None
    latest_ocr_text: Optional[str] = None
    latest_ocr_confidence: Optional[Decimal] = None
    ocr_confirmed: bool = False
    violation_count: int = 0
    first_seen_frame_no: Optional[int] = None
    last_seen_frame_no: Optional[int] = None
    first_seen_at_sec: Optional[Decimal] = None
    last_seen_at_sec: Optional[Decimal] = None
    best_image_path: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
