class BestFrameSelector:
    def is_better(self, candidate: dict, current_best: dict | None) -> bool:
        if current_best is None:
            return True

        candidate_key = (
            candidate["regex_match_count"],
            candidate["person_count"],
            candidate["avg_ocr_confidence"],
        )
        best_key = (
            current_best["regex_match_count"],
            current_best["person_count"],
            current_best["avg_ocr_confidence"],
        )

        if candidate_key != best_key:
            return candidate_key > best_key

        return candidate["frame_no"] < current_best["frame_no"]
