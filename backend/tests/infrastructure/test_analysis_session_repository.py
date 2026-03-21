import pytest
from datetime import datetime
import uuid

from app.domain.entities.analysis_session import AnalysisSession, AnalysisSourceType, AnalysisSessionStatus
from app.infrastructure.db.repositories.analysis_session_repository import SQLAlchemyAnalysisSessionRepository

@pytest.fixture
def repo():
    return SQLAlchemyAnalysisSessionRepository()

def test_save_analysis_session(repo):
    now = datetime.now()
    session_id = f"test-session-{uuid.uuid4().hex[:6]}"
    session = AnalysisSession(
        session_id=session_id,
        source_type=AnalysisSourceType.WEBCAM,
        status=AnalysisSessionStatus.QUEUED,
        frame_interval_sec=3,
        processed_frames=0,
        detected_count=0,
        created_at=now,
        updated_at=now,
        source_name="webcam-0",
        total_frames=10,
        requested_by="tester"
    )
    
    repo.save(session)
    assert session.id is not None
    assert session.id > 0

def test_find_analysis_session_by_session_id(repo):
    now = datetime.now()
    session_id = f"test-session-{uuid.uuid4().hex[:6]}"
    session = AnalysisSession(
        session_id=session_id,
        source_type=AnalysisSourceType.WEBCAM,
        status=AnalysisSessionStatus.QUEUED,
        frame_interval_sec=3,
        processed_frames=0,
        detected_count=0,
        created_at=now,
        updated_at=now
    )
    repo.save(session)
    
    found = repo.find_by_session_id(session_id)
    assert found is not None
    assert found.session_id == session_id
    assert found.source_type == AnalysisSourceType.WEBCAM
    assert found.status == AnalysisSessionStatus.QUEUED
    assert found.frame_interval_sec == 3
    assert found.processed_frames == 0
    assert found.detected_count == 0

def test_update_analysis_session(repo):
    now = datetime.now()
    session_id = f"test-session-{uuid.uuid4().hex[:6]}"
    session = AnalysisSession(
        session_id=session_id,
        source_type=AnalysisSourceType.WEBCAM,
        status=AnalysisSessionStatus.QUEUED,
        frame_interval_sec=3,
        processed_frames=0,
        detected_count=0,
        created_at=now,
        updated_at=now
    )
    repo.save(session)
    
    update_time = datetime.now()
    session.status = AnalysisSessionStatus.COMPLETED
    session.processed_frames = 10
    session.detected_count = 5
    session.finished_at = update_time
    session.updated_at = update_time
    
    repo.update(session)
    
    updated = repo.find_by_session_id(session_id)
    assert updated.status == AnalysisSessionStatus.COMPLETED
    assert updated.processed_frames == 10
    assert updated.detected_count == 5
    assert updated.finished_at == update_time
    assert updated.updated_at == update_time

def test_find_analysis_session_not_found(repo):
    found = repo.find_by_session_id("non-existent-session-id")
    assert found is None
