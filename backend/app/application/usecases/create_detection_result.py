from datetime import datetime
from decimal import Decimal

from app.domain.entities.detection_result import (
    DetectionResult,
    OverallPPEStatus,
    ItemWearStatus,
)


class CreateDetectionResultUseCase:
    def __init__(self, detection_result_repository):
        self.detection_result_repository = detection_result_repository

    def execute(
        self,
        frame_id: int,
        person_index: int,
        employee_no: str | None,
        ocr_text: str | None,
        ocr_confidence: float | None,
        overall_ppe_status: str,
        helmet_status: str,
        vest_status: str,
        person_box_x: int,
        person_box_y: int,
        person_box_width: int,
        person_box_height: int,
        crop_image_path: str | None = None,
    ) -> DetectionResult:
        result = DetectionResult(
            id=None,
            frame_id=frame_id,
            person_index=person_index,
            employee_no=employee_no,
            ocr_text=ocr_text,
            ocr_confidence=Decimal(str(ocr_confidence)) if ocr_confidence is not None else None,
            overall_ppe_status=OverallPPEStatus(overall_ppe_status),
            helmet_status=ItemWearStatus(helmet_status),
            vest_status=ItemWearStatus(vest_status),
            person_box_x=person_box_x,
            person_box_y=person_box_y,
            person_box_width=person_box_width,
            person_box_height=person_box_height,
            crop_image_path=crop_image_path,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.detection_result_repository.save(result)
        return result