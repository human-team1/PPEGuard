from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

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
    session_id: int
    detected_at: datetime
    person_index: int
    overall_ppe_status: OverallPPEStatus
    helmet_status: ItemWearStatus
    vest_status: ItemWearStatus
    created_at: datetime
    updated_at: datetime
    id: int | None = None
    frame_no: int | None = None
    frame_time_sec: Decimal | None = None
    employee_no: str | None = None
    ocr_text: str | None = None
    ocr_confidence: Decimal | None = None
    person_box_x: int | None = None
    person_box_y: int | None = None
    person_box_width: int | None = None
    person_box_height: int | None = None
    image_path: str | None = None
