from sqlalchemy import Column, Integer, BigInteger, String, DateTime, DECIMAL, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.infrastructure.db.base import Base 

class SourceType(enum.Enum):
    WEBCAM = "WEBCAM"
    VIDEO_FILE = "VIDEO_FILE"

class SessionStatus(enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"

class ProcessingStatus(enum.Enum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"

class PPEStatus(enum.Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    UNKNOWN = "UNKNOWN"

class WearStatus(enum.Enum):
    WEARING = "WEARING"
    NOT_WEARING = "NOT_WEARING"
    UNKNOWN = "UNKNOWN"

class AnalysisSessionORM(Base):
    __tablename__ = 'analysis_session'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(50), nullable=False, unique=True, index=True)
    source_type = Column(String(20), nullable=False)
    source_name = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, index=True)
    frame_interval_sec = Column(Integer, nullable=False)
    total_frames = Column(Integer, nullable=True)
    processed_frames = Column(Integer, default=0, nullable=False)
    detected_count = Column(Integer, default=0, nullable=False)
    requested_by = Column(String(100), nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    fail_reason = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    frames = relationship("AnalysisFrameORM", back_populates="session", cascade="all, delete-orphan")

class AnalysisFrameORM(Base):
    __tablename__ = 'analysis_frame'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(BigInteger, ForeignKey('analysis_session.id'), nullable=False)
    frame_no = Column(Integer, nullable=False, index=True)
    frame_time_sec = Column(DECIMAL(10, 2), nullable=False, index=True)
    captured_at = Column(DateTime, nullable=True)
    frame_image_path = Column(String(500), nullable=True)
    person_count = Column(Integer, default=0, nullable=False)
    processing_status = Column(String(20), default="PENDING", nullable=False, index=True)
    error_message = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    session = relationship("AnalysisSessionORM", back_populates="frames")
    results = relationship("DetectionResultORM", back_populates="frame", cascade="all, delete-orphan")

class DetectionResultORM(Base):
    __tablename__ = 'detection_result'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    frame_id = Column(BigInteger, ForeignKey('analysis_frame.id'), nullable=False)
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

    frame = relationship("AnalysisFrameORM", back_populates="results")
