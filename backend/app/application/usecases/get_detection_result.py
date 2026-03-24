from ...domain.entities.detection_result import DetectionResult
from ...domain.ports.service_detection_result_repository import ServiceDetectionResultRepository

class GetDetectionResultUseCase:
    def __init__(self, result_repo: ServiceDetectionResultRepository):
        self.result_repo = result_repo

    def execute(self, result_id: int) -> DetectionResult:
        result = self.result_repo.find_by_id(result_id)
        if not result:
            raise ValueError(f"Result not found: {result_id}]")
        return result 