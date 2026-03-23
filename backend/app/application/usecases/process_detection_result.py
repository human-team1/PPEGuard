from datetime import datetime

from ...domain.entities.detection_result import DetectionResult
from ...domain.ports.repository import (
    AnalysisSessionRepository,
    AnalysisFrameRepository,
    DetectionResultRepository,
)
from ...domain.rules.ppe_validation import (
    get_overall_ppe_status,
    is_valid_worker_id,
    should_save_worker_id,
)
from ..dtos import ProcessDetectionCommand


class ProcessDetectionResultUseCase:
    def __init__(
        self,
        session_repo: AnalysisSessionRepository,
        frame_repo: AnalysisFrameRepository,
        result_repo: DetectionResultRepository,
    ):
        self.session_repo = session_repo
        self.frame_repo = frame_repo
        self.result_repo = result_repo

    def execute(self, cmd: ProcessDetectionCommand):
        session = self.session_repo.find_by_session_id(cmd.session_id)
        if not session or session.id is None:
            raise ValueError(f"Session not found or has no internal DB id: {cmd.session_id}")

        frame = self.frame_repo.find_by_id(cmd.frame_id)
        if not frame:
            raise ValueError(f"Frame not found: {cmd.frame_id}")

        overall_status = get_overall_ppe_status(cmd.helmet_status, cmd.vest_status)

        employee_no = cmd.employee_no
        ocr_text = cmd.ocr_text
        ocr_confidence = cmd.ocr_confidence

        if not should_save_worker_id(ocr_confidence):
            employee_no = None

        if not is_valid_worker_id(employee_no):
            employee_no = None

        now = datetime.now()

        result = DetectionResult(
            frame_id=cmd.frame_id,
            person_index=cmd.person_index,
            overall_ppe_status=overall_status,
            helmet_status=cmd.helmet_status,
            vest_status=cmd.vest_status,
            employee_no=employee_no,
            ocr_text=ocr_text,
            ocr_confidence=ocr_confidence,
            person_box_x=cmd.person_box_x,
            person_box_y=cmd.person_box_y,
            person_box_width=cmd.person_box_width,
            person_box_height=cmd.person_box_height,
            crop_image_path=cmd.crop_image_path,
            created_at=now,
            updated_at=now,
        )

        self.result_repo.save(result)

        # 세션 단위 총 탐지 결과 수 증가
        session.detected_count += 1
        session.updated_at = now
        self.session_repo.update(session)

        # 프레임 단위 사람 수 재계산
        frame_results = self.result_repo.find_by_frame_id(cmd.frame_id)
        frame.person_count = len(frame_results)
        frame.updated_at = now
        self.frame_repo.update(frame)

        return result