import os
from sqlalchemy import Column, Integer, String, DateTime, DECIMAL
from datetime import datetime
from app.infrastructure.customer_db.base import CustomerBase

class CustomerDetectionResultORM(CustomerBase):
    """
    고객사 사내망 DB 전용 DetectionResult 모델
    - MVP에서는 frame_id, session_id 테이블이 고객사 DB에 없으므로 ForeignKey를 지정하지 않습니다.
    """
    __tablename__ = 'detection_result'

    id = Column(Integer, primary_key=True, autoincrement=True)
    frame_id = Column(Integer, nullable=False)
    person_index = Column(Integer, nullable=False)
    employee_no = Column(String(50), nullable=True, index=True)
    ocr_text = Column(String(255), nullable=True)
    ocr_confidence = Column(DECIMAL(5, 4), nullable=True)
    overall_ppe_status = Column(String(20), nullable=False, index=True)
    helmet_status = Column(String(20), nullable=False)
    vest_status = Column(String(20), nullable=False)
    person_box_x = Column(Integer, nullable=True)
    person_box_y = Column(Integer, nullable=True)
    person_box_width = Column(Integer, nullable=True)
    person_box_height = Column(Integer, nullable=True)
    crop_image_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
