from sqlalchemy import Column, String, Integer, DateTime, Numeric, ForeignKey
from app.infrastructure.db.base import Base

class DetectionResultModel(Base):
    __tablename__ = "detection_result"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # analysis_frame.id 참조
    frame_id = Column(Integer, ForeignKey("analysis_frame.id"), nullable=False)

    # 동일 프레임 내 사람 순번
    person_index = Column(Integer, nullable=False)

    # OCR 결과
    employee_no = Column(String(50), nullable=True, index=True)
    ocr_text = Column(String(255), nullable=True)
    ocr_confidence = Column(Numeric(5, 4), nullable=True)

    # PPE 상태
    overall_ppe_status = Column(String(20), nullable=False, index=True)
    helmet_status = Column(String(20), nullable=False)
    vest_status = Column(String(20), nullable=False)

    # 사람 bounding box
    person_box_x = Column(Integer, nullable=True)
    person_box_y = Column(Integer, nullable=True)
    person_box_width = Column(Integer, nullable=True)
    person_box_height = Column(Integer, nullable=True)

    # crop 이미지 경로
    crop_image_path = Column(String(500), nullable=True)

    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)