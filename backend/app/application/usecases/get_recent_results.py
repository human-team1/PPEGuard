from typing import List
from ...domain.entities.detection_result import DetectionResult
from ...domain.ports.service_detection_result_repository import ServiceDetectionResultRepository

class GetRecentResultsUseCase:
    def __init__(self, result_repo: ServiceDetectionResultRepository):
        self.result_repo = result_repo

    def execute(self, limit: int = 20) -> List[DetectionResult]:
        return self.result_repo.find_recent(limit)
