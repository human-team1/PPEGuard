from app.domain.entities.analysis_session import AnalysisSession, AnalysisSourceType, AnalysisSessionStatus
from app.domain.ports.repository import AnalysisSessionRepository
from app.infrastructure.db.models.analysis_session import AnalysisSessionModel
from app.infrastructure.db.session import SessionLocal


class SQLAlchemyAnalysisSessionRepository(AnalysisSessionRepository):
    def _to_domain(self, model: AnalysisSessionModel) -> AnalysisSession:
        return AnalysisSession(
            id=model.id,
            session_id=model.session_id,
            source_type=AnalysisSourceType(model.source_type),
            source_name=model.source_name,
            status=AnalysisSessionStatus(model.status),
            frame_interval_sec=model.frame_interval_sec,
            total_frames=model.total_frames,
            processed_frames=model.processed_frames,
            detected_count=model.detected_count,
            requested_by=model.requested_by,
            started_at=model.started_at,
            finished_at=model.finished_at,
            fail_reason=model.fail_reason,
            created_at=model.created_at,
            updated_at=model.updated_at
        )

    def _to_model(self, domain: AnalysisSession) -> AnalysisSessionModel:
        return AnalysisSessionModel(
            id=domain.id,
            session_id=domain.session_id,
            source_type=domain.source_type.value,
            source_name=domain.source_name,
            status=domain.status.value,
            frame_interval_sec=domain.frame_interval_sec,
            total_frames=domain.total_frames,
            processed_frames=domain.processed_frames,
            detected_count=domain.detected_count,
            requested_by=domain.requested_by,
            started_at=domain.started_at,
            finished_at=domain.finished_at,
            fail_reason=domain.fail_reason,
            created_at=domain.created_at,
            updated_at=domain.updated_at
        )

    def save(self, session: AnalysisSession):
        with SessionLocal() as db_session:
            model = self._to_model(session)
            db_session.add(model)
            db_session.commit()
            db_session.refresh(model)
            session.id = model.id

    def update(self, session: AnalysisSession):
        with SessionLocal() as db_session:
            model = (
                db_session.query(AnalysisSessionModel)
                .filter_by(session_id=session.session_id)
                .first()
            )

            if model:
                model.status = session.status.value
                model.processed_frames = session.processed_frames
                model.detected_count = session.detected_count
                model.started_at = session.started_at
                model.finished_at = session.finished_at
                model.fail_reason = session.fail_reason
                model.updated_at = session.updated_at
                db_session.commit()

    def find_by_session_id(self, session_id: str):
        with SessionLocal() as db_session:
            model = (
                db_session.query(AnalysisSessionModel)
                .filter_by(session_id=session_id)
                .first()
            )
            if model:
                return self._to_domain(model)
            return None