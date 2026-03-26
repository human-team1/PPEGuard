import re


class VideoAnalysisOcrService:
    def __init__(
        self,
        ocr_interval_sec: float,
        employee_no_regex: str,
        employee_number_min_confirm_count: int,
        employee_no_min_length: int,
        employee_no_max_length: int,
    ):
        self.ocr_interval_sec = ocr_interval_sec
        self.employee_no_regex = employee_no_regex
        self.employee_number_min_confirm_count = max(int(employee_number_min_confirm_count or 0), 1)
        self.employee_no_min_length = employee_no_min_length
        self.employee_no_max_length = employee_no_max_length

    def is_person_identified(self, person) -> bool:
        return bool(getattr(person, "ocr_confirmed", False) and getattr(person, "employee_no", None))

    def should_run_ocr_for_person(self, person, current_time_sec: float) -> bool:
        if self.is_person_identified(person):
            return False

        if person.crop_image is None:
            return False

        if getattr(person.crop_image, "size", 0) == 0:
            return False

        last_ocr_at_sec = getattr(person, "last_ocr_at_sec", None)
        if last_ocr_at_sec is None:
            return True

        return (current_time_sec - last_ocr_at_sec) >= self.ocr_interval_sec

    def apply_ocr_result_to_person(self, person, ocr_data: dict | None) -> None:
        person.latest_ocr_candidate = None
        person.latest_ocr_regex_matched = False
        person.latest_ocr_raw_text = None

        if not ocr_data:
            return

        raw_worker_id = (ocr_data or {}).get("worker_id")
        raw_text = (ocr_data or {}).get("raw_text")
        cleaned_text = (ocr_data or {}).get("cleaned_text")
        confidence = float((ocr_data or {}).get("confidence") or 0.0)

        candidate = self.normalize_employee_no(cleaned_text or raw_worker_id or raw_text)
        person.latest_ocr_raw_text = raw_text
        if not candidate:
            return

        person.latest_ocr_candidate = candidate
        if not self.is_valid_employee_no(candidate):
            return

        person.latest_ocr_regex_matched = True
        person.ocr_candidate_counts[candidate] = person.ocr_candidate_counts.get(candidate, 0) + 1
        person.ocr_confidence = confidence
        person.employee_no = candidate
        person.ocr_confirmed = True

    def normalize_employee_no(self, value) -> str | None:
        if value is None:
            return None

        text = str(value).strip()
        if not text:
            return None

        return text

    def is_valid_employee_no(self, employee_no: str) -> bool:
        if not employee_no:
            return False

        if self.employee_no_min_length > 0 and len(employee_no) < self.employee_no_min_length:
            return False

        if self.employee_no_max_length > 0 and len(employee_no) > self.employee_no_max_length:
            return False

        if self.employee_no_regex:
            return re.fullmatch(self.employee_no_regex, employee_no) is not None

        return True
