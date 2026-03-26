from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class SegmentWearStatus(Enum):
    WORN = "WORN"
    NOT_WORN = "NOT_WORN"
    UNKNOWN = "UNKNOWN"


@dataclass
class AnalysisSegmentSummary:
    session_id: int
    segment_index: int
    segment_start_sec: float
    segment_end_sec: float
    representative_frame_path: Optional[str]
    person_count: int
    confirmed_person_count: int
    reference_time: Optional[datetime]
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class AnalysisSegmentPersonResult:
    segment_summary_id: int
    track_id: int
    employee_id: Optional[str]
    ocr_number: Optional[str]
    ocr_confirmed: bool
    helmet_status: SegmentWearStatus
    vest_status: SegmentWearStatus
    observed_frames: int
    helmet_detected_frames: int
    vest_detected_frames: int
    regex_match_count: int
    bbox_x1: Optional[int] = None
    bbox_y1: Optional[int] = None
    bbox_x2: Optional[int] = None
    bbox_y2: Optional[int] = None
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
