from app.domain.entities.analysis_segment import AnalysisSegmentSummary
from app.domain.ports.repository import AnalysisSegmentSummaryRepository
from app.infrastructure.service_db.models.analysis_segment_summary import AnalysisSegmentSummaryModel
from app.infrastructure.service_db.session import SessionLocal


class SQLAlchemyAnalysisSegmentSummaryRepository(AnalysisSegmentSummaryRepository):
    def _to_domain(self, model: AnalysisSegmentSummaryModel) -> AnalysisSegmentSummary:
        return AnalysisSegmentSummary(
            id=model.id,
            session_id=model.session_id,
            segment_index=model.segment_index,
            segment_start_sec=float(model.segment_start_sec),
            segment_end_sec=float(model.segment_end_sec),
            representative_frame_path=model.representative_frame_path,
            person_count=model.person_count,
            confirmed_person_count=model.confirmed_person_count,
            reference_time=model.reference_time,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, domain: AnalysisSegmentSummary) -> AnalysisSegmentSummaryModel:
        return AnalysisSegmentSummaryModel(
            id=domain.id,
            session_id=domain.session_id,
            segment_index=domain.segment_index,
            segment_start_sec=domain.segment_start_sec,
            segment_end_sec=domain.segment_end_sec,
            representative_frame_path=domain.representative_frame_path,
            person_count=domain.person_count,
            confirmed_person_count=domain.confirmed_person_count,
            reference_time=domain.reference_time,
            created_at=domain.created_at,
            updated_at=domain.updated_at,
        )

    def save(self, summary: AnalysisSegmentSummary):
        with SessionLocal() as db_session:
            model = self._to_model(summary)
            db_session.add(model)
            db_session.commit()
            db_session.refresh(model)
            summary.id = model.id

    def find_by_session_id(self, session_id: int):
        with SessionLocal() as db_session:
            models = (
                db_session.query(AnalysisSegmentSummaryModel)
                .filter_by(session_id=session_id)
                .order_by(AnalysisSegmentSummaryModel.segment_index.asc())
                .all()
            )
            return [self._to_domain(model) for model in models]
