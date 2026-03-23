from decimal import Decimal
from app.domain.entities.detection_result import DetectionResult, OverallPPEStatus, ItemWearStatus
from app.domain.ports.repository import DetectionResultRepository
from app.infrastructure.db.models.detection_result import DetectionResultModel
from app.infrastructure.db.models.analysis_frame import AnalysisFrameModel
from app.infrastructure.db.session import SessionLocal

# DetectionResult 엔티티와 ORM 모델을 연결하는 매핑 + 저장 repository
class SQLAlchemyDetectionResultRepository(DetectionResultRepository):
    def _to_domain(self, model):
        return DetectionResult(
            id=model.id,
            frame_id=model.frame_id,
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
            crop_image_path=model.crop_image_path,
            created_at=model.created_at,
            updated_at=model.updated_at
        )

    def _to_model(self, domain):
        return DetectionResultModel(
            id=domain.id,
            frame_id=domain.frame_id,
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
            crop_image_path=domain.crop_image_path,
            created_at=domain.created_at,
            updated_at=domain.updated_at
        )

    def save(self, result):
        with SessionLocal() as db_session:
            model = self._to_model(result)
            db_session.add(model)
            db_session.commit()
            db_session.refresh(model)
            result.id = model.id

    def find_by_frame_id(self, frame_id):
        with SessionLocal() as db_session:
            models = db_session.query(DetectionResultModel).filter_by(frame_id=frame_id).all()
            return [self._to_domain(m) for m in models] 
        
    def find_by_session_id(self, session_id):
        with SessionLocal() as db_session:
            models = (
                db_session.query(DetectionResultModel)
                .join(AnalysisFrameModel, DetectionResultModel.frame_id == AnalysisFrameModel.id)
                .filter(AnalysisFrameModel.session_id == session_id)
                .all()
            )
            return [self._to_domain(m) for m in models]

    def find_recent(self, limit):
        with SessionLocal() as db_session:
            models = (
                db_session.query(DetectionResultModel)
                .order_by(DetectionResultModel.created_at.desc())
                .limit(limit)
                .all()
            )
            return [self._to_domain(m) for m in models]

    def find_by_id(self, id):
        with SessionLocal() as db_session:
            model = db_session.query(DetectionResultModel).filter_by(id=id).first()
            if model:
                return self._to_domain(model)
            return None 
        