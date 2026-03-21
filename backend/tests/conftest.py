import pytest
import os
from sqlalchemy import create_engine
from app.infrastructure.db.base import Base
from app.infrastructure.db.session import SessionLocal

# 중요: 테이블 구조 인식을 위해 모델들을 명시적으로 import
from app.infrastructure.db.models.analysis_session import AnalysisSessionModel
from app.infrastructure.db.models.detection_result import DetectionResultModel

@pytest.fixture(scope="session")
def engine_for_test():
    # 고립된 테스트용 파일 DB 지정
    db_uri = "sqlite:///./test_ppe_guard.db"
    engine = create_engine(db_uri, connect_args={"check_same_thread": False})
    
    # 세션이 테스트 엔진을 바라보도록 전역 설정 변경
    SessionLocal.configure(bind=engine)
    
    yield engine
    
    # 전체 테스트 세션 종료 시 DB 파일 정리
    if os.path.exists("./test_ppe_guard.db"):
        try:
            os.remove("./test_ppe_guard.db")
        except Exception:
            pass

@pytest.fixture(scope="function", autouse=True)
def setup_database(engine_for_test):
    # 각 테스트마다 테이블 내용 초기화(격리)
    Base.metadata.drop_all(bind=engine_for_test)
    Base.metadata.create_all(bind=engine_for_test)
    yield
    # 테스트 후 정리
    Base.metadata.drop_all(bind=engine_for_test)

