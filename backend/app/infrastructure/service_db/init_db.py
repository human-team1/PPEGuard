import logging

from app.infrastructure.service_db.base import Base
from app.infrastructure.service_db.models.analysis_frame import AnalysisFrameModel
from app.infrastructure.service_db.models.analysis_segment_person_result import AnalysisSegmentPersonResultModel
from app.infrastructure.service_db.models.analysis_segment_summary import AnalysisSegmentSummaryModel
from app.infrastructure.service_db.models.analysis_session import AnalysisSessionModel
from app.infrastructure.service_db.models.detection_result import DetectionResultModel
from app.infrastructure.service_db.session import engine


logger = logging.getLogger(__name__)


def create_db_tables():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("[DB] service tables initialization started")
    Base.metadata.create_all(bind=engine)
    logger.info("[DB] service tables initialization completed")


if __name__ == "__main__":
    create_db_tables()
