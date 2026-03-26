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
    video_started_at: Optional[datetime] = None


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
    session_no: Optional[int]
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
class AnalysisSessionListResponseDto:
    sessions: list[AnalysisSessionResponseDto]


@dataclass
class AnalysisFrameItemResponseDto:
    frame_id: int
    frame_no: int
    frame_time_sec: Decimal
    captured_at: Optional[datetime]
    frame_image_path: Optional[str]
    frame_width: Optional[int]
    frame_height: Optional[int]
    person_count: int
    processing_status: str
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class AnalysisFrameListResponseDto:
    session_id: str
    frames: list[AnalysisFrameItemResponseDto] 


@dataclass
class DetectionResultItemResponseDto:
    result_id: int
    frame_id: int
    frame_no: Optional[int]
    frame_time_sec: Optional[Decimal]
    person_index: int
    track_id: Optional[int]
    employee_no: Optional[str]
    ocr_text: Optional[str]
    ocr_confidence: Optional[Decimal]
    overall_ppe_status: str
    helmet_status: str
    vest_status: str
    crop_image_path: Optional[str]
    person_box_x: Optional[int]
    person_box_y: Optional[int]
    person_box_width: Optional[int]
    person_box_height: Optional[int]
    created_at: datetime
    updated_at: datetime

@dataclass
class DetectionResultListResponseDto:
    session_id: str
    results: list[DetectionResultItemResponseDto]
    frames: list[AnalysisFrameItemResponseDto]
    frames: list[AnalysisFrameItemResponseDto]
      
      
@dataclass
class AnalyzeFrameCommand:
    image_base64: str
    session_id: Optional[str] = None
    frame_no: Optional[int] = None


@dataclass
class AnalysisSegmentPersonResultResponseDto:
    person_result_id: int
    local_person_id: int
    track_id: int
    employee_id: Optional[str]
    ocr_number: Optional[str]
    ocr_confirmed: bool
    helmet_status: str
    vest_status: str
    session_final_helmet_status: Optional[str]
    session_final_vest_status: Optional[str]
    observed_frames: int
    helmet_detected_frames: int
    vest_detected_frames: int
    regex_match_count: int
    bbox_x1: Optional[int]
    bbox_y1: Optional[int]
    bbox_x2: Optional[int]
    bbox_y2: Optional[int]
    created_at: datetime
    updated_at: datetime


@dataclass
class AnalysisSegmentSummaryResponseDto:
    segment_id: int
    segment_index: int
    segment_start_sec: float
    segment_end_sec: float
    representative_frame_path: Optional[str]
    person_count: int
    confirmed_person_count: int
    reference_time: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    people: list[AnalysisSegmentPersonResultResponseDto]


@dataclass
class AnalysisSegmentListResponseDto:
    session_id: str
    segments: list[AnalysisSegmentSummaryResponseDto]


@dataclass
class AnalysisTrackSummaryResponseDto:
    track_summary_id: int
    track_id: int
    representative_frame_id: Optional[int]
    representative_frame_path: Optional[str]
    employee_no: Optional[str]
    latest_ocr_text: Optional[str]
    latest_ocr_confidence: Optional[Decimal]
    ocr_confirmed: bool
    overall_ppe_status: str
    helmet_status: str
    vest_status: str
    violation_count: int
    first_seen_frame_no: Optional[int]
    last_seen_frame_no: Optional[int]
    first_seen_at_sec: Optional[Decimal]
    last_seen_at_sec: Optional[Decimal]
    created_at: datetime
    updated_at: datetime


@dataclass
class AnalysisTrackSummaryListResponseDto:
    session_id: str
    tracks: list[AnalysisTrackSummaryResponseDto]

