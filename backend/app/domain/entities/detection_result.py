from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from decimal import Decimal
from typing import Optional


class OverallPPEStatus(Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    UNKNOWN = "UNKNOWN"


class ItemWearStatus(Enum):
    WEARING = "WEARING"
    NOT_WEARING = "NOT_WEARING"
    UNKNOWN = "UNKNOWN"


@dataclass
class DetectionResult:
    frame_id: int
    person_index: int
    overall_ppe_status: OverallPPEStatus
    helmet_status: ItemWearStatus
    vest_status: ItemWearStatus

    track_id: Optional[int] = None
    id: Optional[int] = None
    employee_no: Optional[str] = None
    ocr_text: Optional[str] = None
    ocr_confidence: Optional[Decimal] = None
    person_box_x: Optional[int] = None
    person_box_y: Optional[int] = None
    person_box_width: Optional[int] = None
    person_box_height: Optional[int] = None
    crop_image_path: Optional[str] = None
    frame_no: Optional[int] = None
    frame_time_sec: Optional[Decimal] = None
    detected_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
