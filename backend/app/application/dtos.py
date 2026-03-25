from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from ..domain.entities.analysis_session import AnalysisSourceType, AnalysisSessionStatus
from ..domain.entities.analysis_frame import FrameProcessingStatus
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
    frame_id: int
    person_index: int
    helmet_status: ItemWearStatus
    vest_status: ItemWearStatus
    employee_no: Optional[str] = None
    ocr_text: Optional[str] = None
    ocr_confidence: Optional[float] = None
    person_box_x: Optional[int] = None
    person_box_y: Optional[int] = None
    person_box_width: Optional[int] = None
    person_box_height: Optional[int] = None
    crop_image_path: Optional[str] = None


@dataclass
class AnalysisSessionResponseDto:
    session_id: str
    source_type: str
    source_name: Optional[str]
    status: str
    frame_interval_sec: int
    total_frames: Optional[int]
    processed_frames: int
    detected_count: int
    requested_by: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    fail_reason: Optional[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class AnalysisFrameItemResponseDto:
    frame_id: int
    frame_no: int
    frame_time_sec: Decimal
    captured_at: Optional[datetime]
    frame_image_path: Optional[str]
    person_count: int
    processing_status: str
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class AnalysisFrameListResponseDto:
    session_id: str
    frames: list[AnalysisFrameItemResponseDto]
    frames: list[AnalysisFrameItemResponseDto]
      
      
@dataclass
class AnalyzeFrameCommand:
    image_base64: str