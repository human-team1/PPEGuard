import logging
from app.domain.entities.detection_result import DetectionResult
from app.domain.ports.customer_detection_result_repository import CustomerDetectionResultRepository
from app.infrastructure.customer_db.session import CustomerSessionLocal
from app.infrastructure.customer_db.models.detection_result import CustomerDetectionResultORM

logger = logging.getLogger(__name__)

class SQLAlchemyCustomerDetectionResultRepository(CustomerDetectionResultRepository):
    def save(self, result: DetectionResult):
        """탐지 결과를 고객사 DB에 독립적으로 저장. 예외는 던져서 호출자가 로깅/무시하게 맡김"""
        if not CustomerSessionLocal:
            logger.warning("고객사 DB 연결 설정이 누락되어 저장을 건너뜁니다.")
            raise ConnectionError("Customer DB is not properly configured")

        with CustomerSessionLocal() as db_session:
            model = CustomerDetectionResultORM(
                frame_id=result.frame_id,
                person_index=result.person_index,
                employee_no=result.employee_no,
                ocr_text=result.ocr_text,
                ocr_confidence=result.ocr_confidence,
                overall_ppe_status=result.overall_ppe_status.value,
                helmet_status=result.helmet_status.value,
                vest_status=result.vest_status.value,
                person_box_x=result.person_box_x,
                person_box_y=result.person_box_y,
                person_box_width=result.person_box_width,
                person_box_height=result.person_box_height,
                crop_image_path=result.crop_image_path,
                created_at=result.created_at,
                updated_at=result.updated_at
            )
            db_session.add(model)
            db_session.commit()
            # 고객사 DB에는 ID 갱신을 주입할 필요가 없음(서비스 모델의 ID 기준이 메인)
