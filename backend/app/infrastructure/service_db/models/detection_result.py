from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String

from app.infrastructure.service_db.base import Base


class DetectionResultModel(Base):
    __tablename__ = "detection_result"

    id = Column(Integer, primary_key=True, autoincrement=True)
    frame_id = Column(Integer, ForeignKey("analysis_frame.id"), nullable=False)
    person_index = Column(Integer, nullable=False)
    track_id = Column(Integer, nullable=True, index=True)
    employee_no = Column(String(50), nullable=True, index=True)
    ocr_text = Column(String(255), nullable=True)
    ocr_confidence = Column(Numeric(5, 4), nullable=True)
    overall_ppe_status = Column(String(20), nullable=False, index=True)
    helmet_status = Column(String(20), nullable=False)
    vest_status = Column(String(20), nullable=False)
    person_box_x = Column(Integer, nullable=True)
    person_box_y = Column(Integer, nullable=True)
    person_box_width = Column(Integer, nullable=True)
    person_box_height = Column(Integer, nullable=True)
    crop_image_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
