import logging
from datetime import datetime

from app.domain.entities.detection_result import DetectionResult
from app.domain.ports.repository import (
    AnalysisSessionRepository,
    AnalysisFrameRepository,
)
from app.domain.ports.service_detection_result_repository import ServiceDetectionResultRepository
from app.domain.ports.customer_detection_result_repository import CustomerDetectionResultRepository
from app.domain.rules.ppe_validation import get_overall_ppe_status
from app.application.dtos import ProcessDetectionCommand

logger = logging.getLogger(__name__)


class ProcessDetectionResultUseCase:
    def __init__(
        self,
        session_repo: AnalysisSessionRepository,
        frame_repo: AnalysisFrameRepository,
        result_repo: ServiceDetectionResultRepository,
        customer_result_repo: CustomerDetectionResultRepository = None,
    ):
        self.session_repo = session_repo
        self.frame_repo = frame_repo
        self.result_repo = result_repo
        self.customer_result_repo = customer_result_repo

    def execute(self, cmd: ProcessDetectionCommand):
        session = self.session_repo.find_by_session_id(cmd.session_id)
        if not session or session.id is None:
            raise ValueError(f"Session not found or has no internal DB id: {cmd.session_id}")

        frame = self.frame_repo.find_by_id(cmd.frame_id)
        if not frame:
            raise ValueError(f"Frame not found: {cmd.frame_id}")

        overall_status = get_overall_ppe_status(cmd.helmet_status, cmd.vest_status)
        now = datetime.now()

        result = DetectionResult(
            frame_id=cmd.frame_id,
            person_index=cmd.person_index,
            overall_ppe_status=overall_status,
            helmet_status=cmd.helmet_status,
            vest_status=cmd.vest_status,
            employee_no=cmd.employee_no,
            ocr_text=cmd.ocr_text,
            ocr_confidence=cmd.ocr_confidence,
            person_box_x=cmd.person_box_x,
            person_box_y=cmd.person_box_y,
            person_box_width=cmd.person_box_width,
            person_box_height=cmd.person_box_height,
            crop_image_path=cmd.crop_image_path,
            created_at=now,
            updated_at=now,
        )

        self.result_repo.save(result)

        session.detected_count += 1
        session.updated_at = now
        self.session_repo.update(session)

        frame_results = self.result_repo.find_by_frame_id(cmd.frame_id)
        frame.person_count = len(frame_results)
        frame.updated_at = now
        self.frame_repo.update(frame)

        if self.customer_result_repo:
            try:
                self.customer_result_repo.save(result)
            except Exception as e:
                logger.error(
                    f"고객사 DB에 탐지 결과(ID: {result.id})를 저장하는 중 오류 발생: {e}",
                    exc_info=True,
                )

        return result