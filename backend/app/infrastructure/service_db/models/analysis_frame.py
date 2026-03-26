from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String

from app.infrastructure.service_db.base import Base


class AnalysisFrameModel(Base):
    __tablename__ = "analysis_frame"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("analysis_session.id"), nullable=False)
    frame_no = Column(Integer, nullable=False, index=True)
    frame_time_sec = Column(Numeric(10, 2), nullable=False, index=True)
    captured_at = Column(DateTime, nullable=True)
    frame_image_path = Column(String(500), nullable=True)
    frame_width = Column(Integer, nullable=True)
    frame_height = Column(Integer, nullable=True)
    person_count = Column(Integer, nullable=False, default=0)
    processing_status = Column(String(20), nullable=False, index=True)
    error_message = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
