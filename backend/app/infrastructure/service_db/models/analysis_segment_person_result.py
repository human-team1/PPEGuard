from sqlalchemy import Boolean, Column, Integer, DateTime, String, ForeignKey

from app.infrastructure.service_db.base import Base


class AnalysisSegmentPersonResultModel(Base):
    __tablename__ = "analysis_segment_person_result"

    id = Column(Integer, primary_key=True, autoincrement=True)
    segment_summary_id = Column(Integer, ForeignKey("analysis_segment_summary.id"), nullable=False, index=True)
    track_id = Column(Integer, nullable=False, index=True)
    employee_id = Column(String(50), nullable=True)
    ocr_number = Column(String(50), nullable=True, index=True)
    ocr_confirmed = Column(Boolean, nullable=False, default=False)
    helmet_status = Column(String(20), nullable=False)
    vest_status = Column(String(20), nullable=False)
    observed_frames = Column(Integer, nullable=False, default=0)
    helmet_detected_frames = Column(Integer, nullable=False, default=0)
    vest_detected_frames = Column(Integer, nullable=False, default=0)
    regex_match_count = Column(Integer, nullable=False, default=0)
    bbox_x1 = Column(Integer, nullable=True)
    bbox_y1 = Column(Integer, nullable=True)
    bbox_x2 = Column(Integer, nullable=True)
    bbox_y2 = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
