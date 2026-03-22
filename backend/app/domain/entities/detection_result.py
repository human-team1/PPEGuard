from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from decimal import Decimal
from typing import Optional

class OverallPPEStatus(Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    UNKNOWN = "UNKNOWN"

class ItemWearStatus(Enum):
    WEARING = "WEARING"
    NOT_WEARING = "NOT_WEARING"
    UNKNOWN = "UNKNOWN"

@dataclass
class DetectionResult:
    frame_id: int                            # analysis_frame.id 참조
    person_index: int                        # 동일 프레임 내 사람 순번
    overall_ppe_status: OverallPPEStatus     # 컴플라이언스 여부
    helmet_status: ItemWearStatus            # 헬멧 착용 여부
    vest_status: ItemWearStatus              # 조끼 착용 여부
    
    id: Optional[int] = None                 # 결과 PK
    employee_no: Optional[str] = None        # 사번 (OCR 인식 완료 시)
    ocr_text: Optional[str] = None           # OCR 원문
    ocr_confidence: Optional[Decimal] = None # OCR 신뢰도
    
    person_box_x: Optional[int] = None       # 사람 박스 좌표들
    person_box_y: Optional[int] = None
    person_box_width: Optional[int] = None
    person_box_height: Optional[int] = None
    
    crop_image_path: Optional[str] = None    # 잘라낸 이미지 경로
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
