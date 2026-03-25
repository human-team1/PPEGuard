from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

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
    session_id: str                      # 외부 노출용 식별자 (UUID 등)
    source_type: AnalysisSourceType      # WEBCAM, VIDEO_FILE
    status: AnalysisSessionStatus        # 동작 상태
    frame_interval_sec: int              # 분석 주기
    processed_frames: int = 0            # 처리된 프레임 수
    detected_count: int = 0              # 탐지된 총 건수
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    video_started_at: Optional[datetime] = None
    id: Optional[int] = None             # DB PK
    source_name: Optional[str] = None    # 파일명 등
    total_frames: Optional[int] = None   # 전체 프레임 수
    requested_by: Optional[str] = None   # 요청자
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    fail_reason: Optional[str] = None
