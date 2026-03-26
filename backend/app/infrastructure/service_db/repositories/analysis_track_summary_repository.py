from decimal import Decimal

from app.domain.entities.analysis_track_summary import AnalysisTrackSummary
from app.domain.ports.repository import AnalysisTrackSummaryRepository
from app.infrastructure.service_db.models.analysis_track_summary import AnalysisTrackSummaryModel
from app.infrastructure.service_db.session import SessionLocal


class SQLAlchemyAnalysisTrackSummaryRepository(AnalysisTrackSummaryRepository):
    def _to_domain(self, model: AnalysisTrackSummaryModel) -> AnalysisTrackSummary:
        return AnalysisTrackSummary(
            id=model.id,
            session_id=model.session_id,
            track_id=model.track_id,
            representative_frame_id=model.representative_frame_id,
            employee_no=model.employee_no,
            latest_ocr_text=model.latest_ocr_text,
            latest_ocr_confidence=(
                Decimal(str(model.latest_ocr_confidence))
                if model.latest_ocr_confidence is not None
                else None
            ),
            ocr_confirmed=bool(model.ocr_confirmed),
            overall_ppe_status=model.overall_ppe_status,
            helmet_status=model.helmet_status,
            vest_status=model.vest_status,
            violation_count=model.violation_count,
            first_seen_frame_no=model.first_seen_frame_no,
            last_seen_frame_no=model.last_seen_frame_no,
            first_seen_at_sec=(
                Decimal(str(model.first_seen_at_sec))
                if model.first_seen_at_sec is not None
                else None
            ),
            last_seen_at_sec=(
                Decimal(str(model.last_seen_at_sec))
                if model.last_seen_at_sec is not None
                else None
            ),
            best_image_path=model.best_image_path,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def upsert(self, summary: AnalysisTrackSummary):
        with SessionLocal() as db_session:
            model = (
                db_session.query(AnalysisTrackSummaryModel)
                .filter_by(session_id=summary.session_id, track_id=summary.track_id)
                .first()
            )
            if model is None:
                model = AnalysisTrackSummaryModel(
                    session_id=summary.session_id,
                    track_id=summary.track_id,
                    created_at=summary.created_at,
                    updated_at=summary.updated_at,
                )
                db_session.add(model)

            model.representative_frame_id = summary.representative_frame_id
            model.employee_no = summary.employee_no
            model.latest_ocr_text = summary.latest_ocr_text
            model.latest_ocr_confidence = summary.latest_ocr_confidence
            model.ocr_confirmed = summary.ocr_confirmed
            model.overall_ppe_status = summary.overall_ppe_status
            model.helmet_status = summary.helmet_status
            model.vest_status = summary.vest_status
            model.violation_count = summary.violation_count
            model.first_seen_frame_no = summary.first_seen_frame_no
            model.last_seen_frame_no = summary.last_seen_frame_no
            model.first_seen_at_sec = summary.first_seen_at_sec
            model.last_seen_at_sec = summary.last_seen_at_sec
            model.best_image_path = summary.best_image_path
            model.updated_at = summary.updated_at
            db_session.commit()
            db_session.refresh(model)
            summary.id = model.id

    def find_by_session_id(self, session_id: int):
        with SessionLocal() as db_session:
            models = (
                db_session.query(AnalysisTrackSummaryModel)
                .filter_by(session_id=session_id)
                .order_by(AnalysisTrackSummaryModel.track_id.asc())
                .all()
            )
            return [self._to_domain(model) for model in models]

    def find_by_session_and_track_id(self, session_id: int, track_id: int):
        with SessionLocal() as db_session:
            model = (
                db_session.query(AnalysisTrackSummaryModel)
                .filter_by(session_id=session_id, track_id=track_id)
                .first()
            )
            return self._to_domain(model) if model else None
