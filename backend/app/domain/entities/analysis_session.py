from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class AnalysisSourceType(Enum):
    WEBCAM = "WEBCAM"
    VIDEO_FILE = "VIDEO_FILE"

class AnalysisSessionStatus(Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"

@dataclass
class AnalysisSession:
    session_id: str
    source_type: AnalysisSourceType
    status: AnalysisSessionStatus
    frame_interval_sec: int
    processed_frames: int
    detected_count: int
    created_at: datetime
    updated_at: datetime
    id: int | None = None
    source_name: str | None = None
    total_frames: int | None = None
    requested_by: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    fail_reason: str | None = None
