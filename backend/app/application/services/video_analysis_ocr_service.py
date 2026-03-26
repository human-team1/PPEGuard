import re


class VideoAnalysisOcrService:
    SUPPORTED_INSPECTION_KEYS = {"helmet", "vest"}

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

    def normalize_inspection_item_keys(self, inspection_item_keys: list[str] | None) -> set[str]:
        keys = {
            str(item).strip().lower()
            for item in (inspection_item_keys or [])
            if str(item).strip()
        }
        active_keys = keys & self.SUPPORTED_INSPECTION_KEYS
        return active_keys or set(self.SUPPORTED_INSPECTION_KEYS)

    def get_selected_item_violation_flags(
        self,
        person,
        inspection_item_keys: list[str] | None,
    ) -> dict[str, bool]:
        active_keys = self.normalize_inspection_item_keys(inspection_item_keys)
        flags: dict[str, bool] = {}
        if "helmet" in active_keys:
            flags["helmet"] = not bool(getattr(person, "has_helmet", False))
        if "vest" in active_keys:
            flags["vest"] = not bool(getattr(person, "has_vest", False))
        return flags

    def has_selected_item_violation(
        self,
        person,
        inspection_item_keys: list[str] | None,
    ) -> bool:
        return any(self.get_selected_item_violation_flags(person, inspection_item_keys).values())

    def should_run_ocr_for_person(
        self,
        person,
        current_time_sec: float,
        inspection_item_keys: list[str] | None,
        ocr_attempt_count: int = 0,
        max_attempt_count: int | None = None,
    ) -> bool:
        if self.is_person_identified(person):
            return False

        if person.crop_image is None:
            return False

        if getattr(person.crop_image, "size", 0) == 0:
            return False

        if not self.has_selected_item_violation(person, inspection_item_keys):
            return False

        if max_attempt_count is not None and ocr_attempt_count >= max(int(max_attempt_count), 1):
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
