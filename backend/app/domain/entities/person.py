from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Any

@dataclass
class Person:
    id: int
    bbox: List[int]  # [x1, y1, x2, y2]
    confidence: float
    has_vest: bool = False
    has_helmet: bool = False
    vest_bbox: Optional[List[int]] = None
    vest_confidence: float = 0.0
    helmet_bbox: Optional[List[int]] = None
    helmet_confidence: float = 0.0
    
    # 인텔리전트 트리거 및 상태 관리
    violation_count: int = 0
    crop_image: Optional[Any] = None  # numpy array (cv2 crop)
    last_updated: datetime = field(default_factory=datetime.now)

    def is_safe(self) -> bool:
        """종합 안전 상태 판정 (조끼 + 헬멧 모두 착용 시 Safe)"""
        return self.has_vest and self.has_helmet

    def get_bbox_area(self) -> float:
        """바운딩 박스 면적 계산"""
        x1, y1, x2, y2 = self.bbox
        return (x2 - x1) * (y2 - y1)
