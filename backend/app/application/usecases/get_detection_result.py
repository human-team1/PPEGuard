from ...domain.entities.detection_result import DetectionResult
from ...domain.ports.repository import DetectionResultRepository

class GetDetectionResultUseCase:
    def __init__(self, result_repo):
        self.result_repo = result_repo

    def execute(self, result_id):
        return self.result_repo.find_by_id(result_id)
