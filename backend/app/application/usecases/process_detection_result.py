from datetime import datetime
from ...domain.entities.detection_result import DetectionResult
from ...domain.rules.ppe_validation import evaluate_ppe_status
from ...domain.ports.repository import AnalysisSessionRepository, DetectionResultRepository
from ..dtos import ProcessDetectionCommand

class ProcessDetectionResultUseCase:
    def __init__(self, session_repo: AnalysisSessionRepository, result_repo: DetectionResultRepository):
        self.session_repo = session_repo
        self.result_repo = result_repo

    def execute(self, cmd: ProcessDetectionCommand) -> DetectionResult:
        session = self.session_repo.find_by_session_id(cmd.session_id)
        if not session or session.id is None:
            raise ValueError(f"Session not found or has no internal DB id: {cmd.session_id}")
            
        overall_status = evaluate_ppe_status(cmd.helmet_status, cmd.vest_status)
        
        now = datetime.now()
        result = DetectionResult(
            session_id=session.id,
            detected_at=cmd.detected_at,
            person_index=cmd.person_index,
            overall_ppe_status=overall_status,
            helmet_status=cmd.helmet_status,
            vest_status=cmd.vest_status,
            created_at=now,
            updated_at=now,
            frame_no=cmd.frame_no,
            frame_time_sec=cmd.frame_time_sec,
            employee_no=cmd.employee_no,
            ocr_text=cmd.ocr_text,
            ocr_confidence=cmd.ocr_confidence,
            person_box_x=cmd.person_box_x,
            person_box_y=cmd.person_box_y,
            person_box_width=cmd.person_box_width,
            person_box_height=cmd.person_box_height,
            image_path=cmd.image_path
        )
        
        self.result_repo.save(result)
        
        session.detected_count += 1
        session.updated_at = now
        self.session_repo.update(session)
        
        return result
