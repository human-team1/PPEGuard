from decimal import Decimal
from app.domain.entities.analysis_frame import AnalysisFrame, FrameProcessingStatus
from app.domain.ports.repository import AnalysisFrameRepository
from app.infrastructure.db.models.analysis_frame import AnalysisFrameModel
from app.infrastructure.db.session import SessionLocal

class SQLAlchemyAnalysisFrameRepository(AnalysisFrameRepository):
    def _to_domain(self, model: AnalysisFrameModel) -> AnalysisFrame:
        return AnalysisFrame(
            id=model.id,
            session_id=model.session_id,
            frame_no=model.frame_no,
            frame_time_sec=Decimal(str(model.frame_time_sec)),
            captured_at=model.captured_at,
            frame_image_path=model.frame_image_path,
            person_count=model.person_count,
            processing_status=FrameProcessingStatus(model.processing_status),
            error_message=model.error_message,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, domain: AnalysisFrame) -> AnalysisFrameModel:
        return AnalysisFrameModel(
            id=domain.id,
            session_id=domain.session_id,
            frame_no=domain.frame_no,
            frame_time_sec=domain.frame_time_sec,
            captured_at=domain.captured_at,
            frame_image_path=domain.frame_image_path,
            person_count=domain.person_count,
            processing_status=domain.processing_status.value,
            error_message=domain.error_message,
            created_at=domain.created_at,
            updated_at=domain.updated_at,
        )

    def save(self, frame: AnalysisFrame) -> None:
        with SessionLocal() as db_session:
            model = self._to_model(frame)
            db_session.add(model)
            db_session.commit()
            db_session.refresh(model)
            frame.id = model.id

    def update(self, frame: AnalysisFrame) -> None:
        with SessionLocal() as db_session:
            model = db_session.query(AnalysisFrameModel).filter_by(id=frame.id).first()
            if model:
                model.person_count = frame.person_count
                model.processing_status = frame.processing_status.value
                model.error_message = frame.error_message
                model.frame_image_path = frame.frame_image_path
                model.captured_at = frame.captured_at
                model.updated_at = frame.updated_at
                db_session.commit()

    def find_by_id(self, id: int) -> AnalysisFrame | None:
        with SessionLocal() as db_session:
            model = db_session.query(AnalysisFrameModel).filter_by(id=id).first()
            if model:
                return self._to_domain(model)
            return None

    def find_by_session_id(self, session_id: int) -> list[AnalysisFrame]:
        with SessionLocal() as db_session:
            models = (
                db_session.query(AnalysisFrameModel)
                .filter_by(session_id=session_id)
                .order_by(AnalysisFrameModel.frame_no.asc())
                .all()
            )
            return [self._to_domain(m) for m in models]