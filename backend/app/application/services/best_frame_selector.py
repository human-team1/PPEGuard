class BestFrameSelector:
    def is_better(self, candidate: dict, current_best: dict | None) -> bool:
        if current_best is None:
            return True

        candidate_key = (
            candidate["confirmed_ocr_person_count"],
            candidate["violation_person_count"],
            candidate["regex_match_count"],
            candidate["max_bbox_area"],
            candidate["person_count"],
            candidate["avg_ocr_confidence"],
        )
        best_key = (
            current_best["confirmed_ocr_person_count"],
            current_best["violation_person_count"],
            current_best["regex_match_count"],
            current_best["max_bbox_area"],
            current_best["person_count"],
            current_best["avg_ocr_confidence"],
        )

        if candidate_key != best_key:
            return candidate_key > best_key

        return candidate["frame_no"] < current_best["frame_no"]
