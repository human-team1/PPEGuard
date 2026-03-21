from typing import List
from ...domain.entities.detection_result import DetectionResult
from ...domain.ports.repository import DetectionResultRepository

class GetRecentResultsUseCase:
    def __init__(self, result_repo: DetectionResultRepository):
        self.result_repo = result_repo

    def execute(self, limit: int = 20) -> List[DetectionResult]:
        return self.result_repo.find_recent(limit)
