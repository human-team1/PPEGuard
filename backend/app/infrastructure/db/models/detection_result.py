from sqlalchemy import Column, String, Integer, DateTime, Numeric, ForeignKey
from app.infrastructure.db.base import Base

class DetectionResultModel(Base):
    __tablename__ = "detection_result"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("analysis_session.id"), nullable=False)
    frame_no = Column(Integer, nullable=True)
    frame_time_sec = Column(Numeric(10, 2), nullable=True)
    detected_at = Column(DateTime, nullable=False)
    person_index = Column(Integer, nullable=False)
    employee_no = Column(String(50), nullable=True)
    ocr_text = Column(String(255), nullable=True)
    ocr_confidence = Column(Numeric(5, 4), nullable=True)
    overall_ppe_status = Column(String(20), nullable=False)
    helmet_status = Column(String(20), nullable=False)
    vest_status = Column(String(20), nullable=False)
    person_box_x = Column(Integer, nullable=True)
    person_box_y = Column(Integer, nullable=True)
    person_box_width = Column(Integer, nullable=True)
    person_box_height = Column(Integer, nullable=True)
    image_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
