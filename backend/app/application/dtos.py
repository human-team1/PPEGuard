from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from ..domain.entities.analysis_session import AnalysisSourceType
from ..domain.entities.detection_result import ItemWearStatus

@dataclass
class StartSessionCommand:
    source_type: AnalysisSourceType
    frame_interval_sec: int
    source_name: Optional[str] = None
    total_frames: Optional[int] = None
    requested_by: Optional[str] = None

@dataclass
class ProcessDetectionCommand:
    session_id: str
    detected_at: datetime
    person_index: int
    helmet_status: ItemWearStatus
    vest_status: ItemWearStatus
    frame_no: Optional[int] = None
    frame_time_sec: Optional[Decimal] = None
    employee_no: Optional[str] = None
    ocr_text: Optional[str] = None
    ocr_confidence: Optional[Decimal] = None
    person_box_x: Optional[int] = None
    person_box_y: Optional[int] = None
    person_box_width: Optional[int] = None
    person_box_height: Optional[int] = None
    image_path: Optional[str] = None
