from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from decimal import Decimal
from typing import Optional

class FrameProcessingStatus(Enum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"

@dataclass
class AnalysisFrame:
    session_id: int                    # analysis_session.id 참조
    frame_no: int                      # 프레임 번호
    frame_time_sec: Decimal            # 영상 내 시간(초)
    person_count: int = 0              # 탐지된 사람 수
    processing_status: FrameProcessingStatus = FrameProcessingStatus.PENDING
    id: Optional[int] = None           # 프레임 PK
    captured_at: Optional[datetime] = None
    frame_image_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
