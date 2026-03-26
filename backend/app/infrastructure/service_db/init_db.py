import logging

from sqlalchemy import text

from app.infrastructure.service_db.base import Base
from app.infrastructure.service_db.models.analysis_frame import AnalysisFrameModel
from app.infrastructure.service_db.models.analysis_segment_person_result import AnalysisSegmentPersonResultModel
from app.infrastructure.service_db.models.analysis_segment_summary import AnalysisSegmentSummaryModel
from app.infrastructure.service_db.models.analysis_session import AnalysisSessionModel
from app.infrastructure.service_db.models.analysis_track_summary import AnalysisTrackSummaryModel
from app.infrastructure.service_db.models.detection_result import DetectionResultModel
from app.infrastructure.service_db.session import engine


logger = logging.getLogger(__name__)


def create_db_tables():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("[DB] service tables initialization started")
    Base.metadata.create_all(bind=engine)
    _ensure_analysis_frame_columns()
    _ensure_detection_result_columns()
    _ensure_segment_person_result_columns()
    logger.info("[DB] service tables initialization completed")


def _ensure_analysis_frame_columns():
    required_columns = {
        "frame_width": "INTEGER",
        "frame_height": "INTEGER",
    }
    _ensure_columns("analysis_frame", required_columns)


def _ensure_detection_result_columns():
    required_columns = {
        "track_id": "INTEGER",
    }
    _ensure_columns("detection_result", required_columns)


def _ensure_segment_person_result_columns():
    required_columns = {
        "bbox_x1": "INTEGER",
        "bbox_y1": "INTEGER",
        "bbox_x2": "INTEGER",
        "bbox_y2": "INTEGER",
    }
    _ensure_columns("analysis_segment_person_result", required_columns)


def _ensure_columns(table_name: str, required_columns: dict[str, str]):
    with engine.begin() as connection:
        column_rows = connection.execute(
            text(f"PRAGMA table_info({table_name})")
        ).fetchall()
        existing_columns = {row[1] for row in column_rows}
        for column_name, column_type in required_columns.items():
            if column_name in existing_columns:
                continue
            connection.execute(
                text(
                    f"ALTER TABLE {table_name} "
                    f"ADD COLUMN {column_name} {column_type}"
                )
            )


if __name__ == "__main__":
    create_db_tables()
