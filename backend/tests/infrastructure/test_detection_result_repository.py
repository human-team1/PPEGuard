import pytest
from datetime import datetime
from decimal import Decimal
import uuid

from app.domain.entities.analysis_session import AnalysisSession, AnalysisSourceType, AnalysisSessionStatus
from app.domain.entities.detection_result import DetectionResult, OverallPPEStatus, ItemWearStatus
from app.infrastructure.db.repositories.analysis_session_repository import SQLAlchemyAnalysisSessionRepository
from app.infrastructure.db.repositories.detection_result_repository import SQLAlchemyDetectionResultRepository

@pytest.fixture
def session_repo():
    return SQLAlchemyAnalysisSessionRepository()

@pytest.fixture
def result_repo():
    return SQLAlchemyDetectionResultRepository()

@pytest.fixture
def saved_session(session_repo):
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
    session_repo.save(session)
    return session

def test_save_detection_result(result_repo, saved_session):
    now = datetime.now()
    result = DetectionResult(
        session_id=saved_session.id,
        detected_at=now,
        person_index=1,
        overall_ppe_status=OverallPPEStatus.COMPLIANT,
        helmet_status=ItemWearStatus.WEARING,
        vest_status=ItemWearStatus.WEARING,
        created_at=now,
        updated_at=now,
        frame_no=1,
        frame_time_sec=Decimal("0.00"),
        employee_no="E1001",
        ocr_text="E1001",
        ocr_confidence=Decimal("0.9500"),
        person_box_x=10,
        person_box_y=20,
        person_box_width=100,
        person_box_height=200,
        image_path="uploads/test_001.jpg"
    )
    
    result_repo.save(result)
    assert result.id is not None
    assert result.id > 0

def test_find_detection_results_by_session_id(result_repo, saved_session):
    now = datetime.now()
    result = DetectionResult(
        session_id=saved_session.id,
        detected_at=now,
        person_index=1,
        overall_ppe_status=OverallPPEStatus.COMPLIANT,
        helmet_status=ItemWearStatus.WEARING,
        vest_status=ItemWearStatus.WEARING,
        created_at=now,
        updated_at=now,
        image_path="uploads/test_001.jpg"
    )
    result_repo.save(result)
    
    results = result_repo.find_by_session_id(saved_session.id)
    assert len(results) >= 1
    found = results[0]
    assert found.session_id == saved_session.id
    assert found.person_index == 1
    assert found.overall_ppe_status == OverallPPEStatus.COMPLIANT
    assert found.helmet_status == ItemWearStatus.WEARING
    assert found.vest_status == ItemWearStatus.WEARING
    assert found.image_path == "uploads/test_001.jpg"

def test_find_detection_result_by_id(result_repo, saved_session):
    now = datetime.now()
    result = DetectionResult(
        session_id=saved_session.id,
        detected_at=now,
        person_index=2,
        overall_ppe_status=OverallPPEStatus.NON_COMPLIANT,
        helmet_status=ItemWearStatus.NOT_WEARING,
        vest_status=ItemWearStatus.WEARING,
        created_at=now,
        updated_at=now
    )
    result_repo.save(result)
    
    found = result_repo.find_by_id(result.id)
    assert found is not None
    assert found.id == result.id
    assert found.person_index == 2
    assert found.overall_ppe_status == OverallPPEStatus.NON_COMPLIANT

def test_find_recent_detection_results(result_repo, saved_session):
    now = datetime.now()
    result1 = DetectionResult(
        session_id=saved_session.id,
        detected_at=now,
        person_index=1,
        overall_ppe_status=OverallPPEStatus.COMPLIANT,
        helmet_status=ItemWearStatus.WEARING,
        vest_status=ItemWearStatus.WEARING,
        created_at=now,
        updated_at=now
    )
    result2 = DetectionResult(
        session_id=saved_session.id,
        detected_at=now,
        person_index=2,
        overall_ppe_status=OverallPPEStatus.NON_COMPLIANT,
        helmet_status=ItemWearStatus.WEARING,
        vest_status=ItemWearStatus.NOT_WEARING,
        created_at=now,
        updated_at=now
    )
    result_repo.save(result1)
    result_repo.save(result2)
    
    # recent_results 는 현재 구현상 created_at의 desc() 로 정렬됨
    recent_results = result_repo.find_recent(limit=10)
    assert len(recent_results) >= 2
    
    ids = [r.id for r in recent_results]
    assert result1.id in ids
    assert result2.id in ids

def test_find_detection_result_not_found(result_repo):
    found = result_repo.find_by_id(999999)
    assert found is None
