from app.infrastructure.service_db.session import engine
from app.infrastructure.service_db.base import Base

# 이 모듈들이 임포트되어야 Base.metadata가 테이블을 인식합니다.
from app.infrastructure.service_db.models.analysis_session import AnalysisSessionModel
from app.infrastructure.service_db.models.analysis_frame import AnalysisFrameModel
from app.infrastructure.service_db.models.detection_result import DetectionResultModel
from app.infrastructure.service_db.models.analysis_segment_summary import AnalysisSegmentSummaryModel
from app.infrastructure.service_db.models.analysis_segment_person_result import AnalysisSegmentPersonResultModel

def create_db_tables():
    print("서비스 내부 DB 테이블 생성을 시작합니다...")
    Base.metadata.create_all(bind=engine)
    print("테이블 생성이 완료되었습니다.")

if __name__ == "__main__":
    create_db_tables()
