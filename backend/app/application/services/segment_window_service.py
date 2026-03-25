class SegmentWindowService:
    SEGMENT_SECONDS = 10.0

    def get_segment_index(self, elapsed_sec: float) -> int:
        if elapsed_sec < 0:
            return 0
        return int(elapsed_sec // self.SEGMENT_SECONDS)

    def get_segment_start_sec(self, segment_index: int) -> float:
        return float(segment_index * self.SEGMENT_SECONDS)

    def get_segment_end_sec(self, segment_index: int, actual_end_sec: float | None = None) -> float:
        default_end_sec = float((segment_index + 1) * self.SEGMENT_SECONDS)
        if actual_end_sec is None:
            return default_end_sec
        return min(default_end_sec, float(actual_end_sec))
