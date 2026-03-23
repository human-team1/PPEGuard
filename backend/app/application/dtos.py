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
    session_id: str # analysis_session.session_id (세션 카운트 갱신용)
    frame_id: int   # analysis_frame.id
    person_index: int
    helmet_status: ItemWearStatus
    vest_status: ItemWearStatus
    employee_no: Optional[str] = None
    ocr_text: Optional[str] = None
    ocr_confidence: Optional[Decimal] = None
    person_box_x: Optional[int] = None
    person_box_y: Optional[int] = None
    person_box_width: Optional[int] = None
    person_box_height: Optional[int] = None
    crop_image_path: Optional[str] = None