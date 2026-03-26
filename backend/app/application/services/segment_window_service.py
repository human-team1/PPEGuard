from config.settings import Config


class SegmentWindowService:
    def __init__(self, segment_seconds: float | None = None):
        self.segment_seconds = float(segment_seconds or Config.SEGMENT_DURATION_SECONDS)

    def get_segment_index(self, elapsed_sec: float) -> int:
        if elapsed_sec < 0:
            return 0
        return int(elapsed_sec // self.segment_seconds)

    def get_segment_start_sec(self, segment_index: int) -> float:
        return float(segment_index * self.segment_seconds)

    def get_segment_end_sec(self, segment_index: int, actual_end_sec: float | None = None) -> float:
        default_end_sec = float((segment_index + 1) * self.segment_seconds)
        if actual_end_sec is None:
            return default_end_sec
        return min(default_end_sec, float(actual_end_sec))
