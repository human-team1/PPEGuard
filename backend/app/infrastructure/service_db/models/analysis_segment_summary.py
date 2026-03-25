from sqlalchemy import Column, Integer, DateTime, Numeric, String, ForeignKey

from app.infrastructure.service_db.base import Base


class AnalysisSegmentSummaryModel(Base):
    __tablename__ = "analysis_segment_summary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("analysis_session.id"), nullable=False, index=True)
    segment_index = Column(Integer, nullable=False, index=True)
    segment_start_sec = Column(Numeric(10, 2), nullable=False)
    segment_end_sec = Column(Numeric(10, 2), nullable=False)
    representative_frame_path = Column(String(500), nullable=True)
    person_count = Column(Integer, nullable=False, default=0)
    confirmed_person_count = Column(Integer, nullable=False, default=0)
    reference_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
