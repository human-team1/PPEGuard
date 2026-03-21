from sqlalchemy import Column, String, Integer, DateTime
from app.infrastructure.db.base import Base

class AnalysisSessionModel(Base):
    __tablename__ = "analysis_session"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), unique=True, nullable=False)
    source_type = Column(String(20), nullable=False)
    source_name = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False)
    frame_interval_sec = Column(Integer, nullable=False)
    total_frames = Column(Integer, nullable=True)
    processed_frames = Column(Integer, nullable=False, default=0)
    detected_count = Column(Integer, nullable=False, default=0)
    requested_by = Column(String(100), nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    fail_reason = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
