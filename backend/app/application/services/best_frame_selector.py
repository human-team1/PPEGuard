class BestFrameSelector:
    def is_better(self, candidate: dict, current_best: dict | None) -> bool:
        if current_best is None:
            return True

        candidate_key = (
            candidate["violation_person_count"],
            candidate["confirmed_violation_person_count"],
        )
        best_key = (
            current_best["violation_person_count"],
            current_best["confirmed_violation_person_count"],
        )

        if candidate_key != best_key:
            return candidate_key > best_key

        return candidate["frame_no"] < current_best["frame_no"]
