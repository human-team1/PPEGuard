from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class FrameProcessingStatus(Enum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


@dataclass
class AnalysisFrame:
    session_id: int
    frame_no: int
    frame_time_sec: Decimal
    person_count: int = 0
    processing_status: FrameProcessingStatus = FrameProcessingStatus.PENDING
    id: Optional[int] = None
    captured_at: Optional[datetime] = None
    frame_image_path: Optional[str] = None
    frame_width: Optional[int] = None
    frame_height: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
