from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint

from app.infrastructure.service_db.base import Base


class AnalysisTrackSummaryModel(Base):
    __tablename__ = "analysis_track_summary"
    __table_args__ = (
        UniqueConstraint("session_id", "track_id", name="uq_analysis_track_summary_session_track"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("analysis_session.id"), nullable=False, index=True)
    track_id = Column(Integer, nullable=False, index=True)
    representative_frame_id = Column(Integer, ForeignKey("analysis_frame.id"), nullable=True)
    employee_no = Column(String(50), nullable=True, index=True)
    latest_ocr_text = Column(String(255), nullable=True)
    latest_ocr_confidence = Column(Numeric(5, 4), nullable=True)
    ocr_confirmed = Column(Boolean, nullable=False, default=False)
    overall_ppe_status = Column(String(20), nullable=False, index=True)
    helmet_status = Column(String(20), nullable=False)
    vest_status = Column(String(20), nullable=False)
    violation_count = Column(Integer, nullable=False, default=0)
    first_seen_frame_no = Column(Integer, nullable=True)
    last_seen_frame_no = Column(Integer, nullable=True)
    first_seen_at_sec = Column(Numeric(10, 2), nullable=True)
    last_seen_at_sec = Column(Numeric(10, 2), nullable=True)
    best_image_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
