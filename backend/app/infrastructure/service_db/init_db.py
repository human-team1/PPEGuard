import sys
import os

# PYTHONPATH 설정 (직접 실행 시 모듈 임포트 가능)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from app.infrastructure.service_db.session import engine
from app.infrastructure.service_db.base import Base

# 이 모듈들이 임포트되어야 Base.metadata가 테이블을 인식합니다.
from app.infrastructure.service_db.models.analysis_session import AnalysisSessionModel
from app.infrastructure.service_db.models.analysis_frame import AnalysisFrameModel
from app.infrastructure.service_db.models.detection_result import DetectionResultModel

def create_db_tables():
    print("서비스 내부 DB 테이블 생성을 시작합니다...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✓ 테이블 생성이 완료되었습니다.")
        return True
    except Exception as e:
        print(f"✗ 테이블 생성 중 오류가 발생했습니다: {str(e)}")
        return False

if __name__ == "__main__":
    create_db_tables()
