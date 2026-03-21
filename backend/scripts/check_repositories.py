import os
import sys

# Ensure backend root is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set explicitly to a test DB
os.environ["SERVICE_DATABASE_URI"] = "sqlite:///./test_ppe_guard.db"

from datetime import datetime
from decimal import Decimal
import uuid

from app.domain.entities.analysis_session import AnalysisSession, AnalysisSourceType, AnalysisSessionStatus
from app.domain.entities.detection_result import DetectionResult, OverallPPEStatus, ItemWearStatus
from app.infrastructure.db.base import Base
from app.infrastructure.db.session import engine
from app.infrastructure.db.repositories.analysis_session_repository import SQLAlchemyAnalysisSessionRepository
from app.infrastructure.db.repositories.detection_result_repository import SQLAlchemyDetectionResultRepository

def run_checks():
    print("1. 테스트용 DB 및 테이블 생성...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    session_repo = SQLAlchemyAnalysisSessionRepository()
    result_repo = SQLAlchemyDetectionResultRepository()

    print("2. AnalysisSession 생성 및 저장 (save)")
    now = datetime.now()
    test_session_id = f"test-session-001"
    
    new_session = AnalysisSession(
        session_id=test_session_id,
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
    
    session_repo.save(new_session)
    assert new_session.id is not None, "DB 저장 후 id가 바인딩되어야 합니다."
    print(f" -> 성공 (생성된 PK = {new_session.id})")
    
    print("3. AnalysisSession 다시 조회 (find_by_session_id)")
    found_session = session_repo.find_by_session_id(test_session_id)
    assert found_session is not None
    assert found_session.status == AnalysisSessionStatus.QUEUED
    print(f" -> 성공 (조회된 session_id: {found_session.session_id}, 상태: {found_session.status.name})")

    print("4. AnalysisSession 변경 및 수정 반영 (update)")
    update_time = datetime.now()
    found_session.status = AnalysisSessionStatus.COMPLETED
    found_session.processed_frames = 10
    found_session.detected_count = 5
    found_session.finished_at = update_time
    found_session.updated_at = update_time
    
    session_repo.update(found_session)
    
    updated_session = session_repo.find_by_session_id(test_session_id)
    assert updated_session.status == AnalysisSessionStatus.COMPLETED
    print(f" -> 성공 (업데이트된 상태: {updated_session.status.name}, 처리 프레임: {updated_session.processed_frames})")

    print("5. DetectionResult 생성 및 FK 반영 저장 (save)")
    result_now = datetime.now()
    new_result = DetectionResult(
        session_id=updated_session.id, # FK
        detected_at=result_now,
        person_index=1,
        overall_ppe_status=OverallPPEStatus.COMPLIANT,
        helmet_status=ItemWearStatus.WEARING,
        vest_status=ItemWearStatus.WEARING,
        created_at=result_now,
        updated_at=result_now,
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
    
    result_repo.save(new_result)
    assert new_result.id is not None
    print(f" -> 성공 (생성된 DetectionResult PK = {new_result.id})")

    print("6. DetectionResult 전체 목록 조회 (find_by_session_id)")
    results_by_session = result_repo.find_by_session_id(updated_session.id)
    assert len(results_by_session) >= 1
    print(f" -> 성공 (해당 세션의 결과 수: {len(results_by_session)}건)")

    print("7. DetectionResult ID 기준 단건 조회 (find_by_id)")
    found_result = result_repo.find_by_id(new_result.id)
    assert found_result is not None
    print(f" -> 성공 (조회된 사번: {found_result.employee_no}, 헬멧 상태: {found_result.helmet_status.name})")

    print("8. DetectionResult 최근 결과 조회 (find_recent)")
    recent_results = result_repo.find_recent(limit=5)
    assert len(recent_results) >= 1
    print(f" -> 성공 (최근 결과 조회: {len(recent_results)}건)")
    
    print("\n[DB Verification Successful] 모든 저장/조회 동작 테스트 통과!")

if __name__ == "__main__":
    run_checks()
