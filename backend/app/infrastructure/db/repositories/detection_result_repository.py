from decimal import Decimal
from app.domain.entities.detection_result import DetectionResult, OverallPPEStatus, ItemWearStatus
from app.domain.ports.repository import DetectionResultRepository
from app.infrastructure.db.models.detection_result import DetectionResultModel
from app.infrastructure.db.session import SessionLocal

class SQLAlchemyDetectionResultRepository(DetectionResultRepository):
    def _to_domain(self, model: DetectionResultModel) -> DetectionResult:
        return DetectionResult(
            id=model.id,
            session_id=model.session_id,
            frame_no=model.frame_no,
            frame_time_sec=Decimal(str(model.frame_time_sec)) if model.frame_time_sec is not None else None,
            detected_at=model.detected_at,
            person_index=model.person_index,
            employee_no=model.employee_no,
            ocr_text=model.ocr_text,
            ocr_confidence=Decimal(str(model.ocr_confidence)) if model.ocr_confidence is not None else None,
            overall_ppe_status=OverallPPEStatus(model.overall_ppe_status),
            helmet_status=ItemWearStatus(model.helmet_status),
            vest_status=ItemWearStatus(model.vest_status),
            person_box_x=model.person_box_x,
            person_box_y=model.person_box_y,
            person_box_width=model.person_box_width,
            person_box_height=model.person_box_height,
            image_path=model.image_path,
            created_at=model.created_at,
            updated_at=model.updated_at
        )

    def _to_model(self, domain: DetectionResult) -> DetectionResultModel:
        return DetectionResultModel(
            id=domain.id,
            session_id=domain.session_id,
            frame_no=domain.frame_no,
            frame_time_sec=domain.frame_time_sec,
            detected_at=domain.detected_at,
            person_index=domain.person_index,
            employee_no=domain.employee_no,
            ocr_text=domain.ocr_text,
            ocr_confidence=domain.ocr_confidence,
            overall_ppe_status=domain.overall_ppe_status.value,
            helmet_status=domain.helmet_status.value,
            vest_status=domain.vest_status.value,
            person_box_x=domain.person_box_x,
            person_box_y=domain.person_box_y,
            person_box_width=domain.person_box_width,
            person_box_height=domain.person_box_height,
            image_path=domain.image_path,
            created_at=domain.created_at,
            updated_at=domain.updated_at
        )

    def save(self, result: DetectionResult) -> None:
        with SessionLocal() as db_session:
            model = self._to_model(result)
            db_session.add(model)
            db_session.commit()
            db_session.refresh(model)
            result.id = model.id

    def find_by_session_id(self, session_id: int) -> list[DetectionResult]:
        with SessionLocal() as db_session:
            models = db_session.query(DetectionResultModel).filter_by(session_id=session_id).all()
            return [self._to_domain(m) for m in models]

    def find_recent(self, limit: int) -> list[DetectionResult]:
        with SessionLocal() as db_session:
            models = db_session.query(DetectionResultModel).order_by(DetectionResultModel.created_at.desc()).limit(limit).all()
            return [self._to_domain(m) for m in models]

    def find_by_id(self, id: int) -> DetectionResult | None:
        with SessionLocal() as db_session:
            model = db_session.query(DetectionResultModel).filter_by(id=id).first()
            if model:
                return self._to_domain(model)
            return None
