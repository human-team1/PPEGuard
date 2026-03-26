from dataclasses import dataclass
from datetime import datetime
from typing import Any


def parse_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def format_datetime(value):
    parsed = parse_datetime(value)
    if parsed is None:
        return "-"
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def map_overall_ppe_status(
    helmet_status: str,
    vest_status: str,
    active_items: set[str],
) -> str:
    checks = []
    if "helmet" in active_items:
        checks.append(helmet_status)
    if "vest" in active_items:
        checks.append(vest_status)

    if not checks:
        return "정상"
    if any(status == "NOT_WORN" for status in checks):
        return "위반"
    if all(status == "UNKNOWN" for status in checks):
        return "미확인"
    if all(status == "WORN" for status in checks):
        return "정상"
    return "미확인"


def map_violation_type(
    helmet_status: str,
    vest_status: str,
    active_items: set[str],
) -> str:
    labels = []
    if "helmet" in active_items and helmet_status == "NOT_WORN":
        labels.append("헬멧")
    if "vest" in active_items and vest_status == "NOT_WORN":
        labels.append("조끼")
    return ", ".join(labels) if labels else "-"


def get_effective_person_status(person: dict[str, Any], field_name: str) -> str:
    return (
        person.get(f"session_final_{field_name}")
        or person.get(field_name)
        or "UNKNOWN"
    )


def get_latest_segment(segments: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not segments:
        return None
    return max(
        segments,
        key=lambda item: (
            int(item.get("segment_index") or 0),
            float(item.get("segment_end_sec") or 0),
            int(item.get("segment_id") or 0),
        ),
    )


def calculate_live_monitor_kpis(
    latest_segment: dict[str, Any] | None,
    total_segments: int,
    active_items: list[str] | None = None,
) -> dict[str, str]:
    active_set = set(active_items or [])
    people = (latest_segment or {}).get("people", [])
    current_people = len(people)
    current_violations = 0

    for person in people:
        status = map_overall_ppe_status(
            person.get("helmet_status", "UNKNOWN"),
            person.get("vest_status", "UNKNOWN"),
            active_set,
        )
        if status == "위반":
            current_violations += 1

    violation_rate = 0.0
    if current_people > 0:
        violation_rate = (current_violations / current_people) * 100.0

    return {
        "current_people": str(current_people),
        "current_violations": str(current_violations),
        "current_violation_rate": f"{violation_rate:.1f}%" if violation_rate % 1 else f"{int(violation_rate)}%",
        "total_segments": str(total_segments),
    }


@dataclass
class SessionPersonRowDto:
    person_result_id: int | None
    segment_id: int
    segment_index: int
    local_person_id: int | None
    segment_label: str
    reference_time: str
    employee_id: str
    ocr_number: str
    ocr_confirmed: str
    helmet_status: str
    vest_status: str
    overall_ppe_status: str
    violation_type: str


@dataclass
class SessionDashboardDto:
    session_id: str
    total_segments: int
    total_detected_people: int
    total_violation_people: int
    total_confirmed_people: int
    rows: list[SessionPersonRowDto]
    status_ratio: dict[str, int]
    segment_violation_counts: dict[str, int]
    source_segments: list[dict[str, Any]]

    @classmethod
    def from_segments_api(
        cls,
        payload: dict[str, Any],
        filters: dict[str, str] | None = None,
        active_items: list[str] | None = None,
    ):
        filters = filters or {}
        active_item_set = set(active_items or [])
        session_id = payload.get("session_id", "")
        segments = payload.get("segments", [])

        unique_rows: dict[tuple, SessionPersonRowDto] = {}
        total_segments = len({segment.get("segment_id") for segment in segments})

        for segment in segments:
            segment_label = (
                f"{int(segment.get('segment_start_sec', 0)):02d}s"
                f" ~ {int(segment.get('segment_end_sec', 0)):02d}s"
            )
            reference_time = format_datetime(
                segment.get("reference_time") or segment.get("created_at")
            )

            for person in segment.get("people", []):
                helmet_status = get_effective_person_status(person, "helmet_status")
                vest_status = get_effective_person_status(person, "vest_status")
                row = SessionPersonRowDto(
                    person_result_id=person.get("person_result_id"),
                    segment_id=segment.get("segment_id", 0),
                    segment_index=segment.get("segment_index", 0),
                    local_person_id=person.get("local_person_id", person.get("track_id")),
                    segment_label=segment_label,
                    reference_time=reference_time,
                    employee_id=person.get("employee_id") or "-",
                    ocr_number=person.get("ocr_number") or "-",
                    ocr_confirmed="Y" if bool(person.get("ocr_confirmed")) else "N",
                    helmet_status=helmet_status,
                    vest_status=vest_status,
                    overall_ppe_status=map_overall_ppe_status(
                        helmet_status,
                        vest_status,
                        active_item_set,
                    ),
                    violation_type=map_violation_type(
                        helmet_status,
                        vest_status,
                        active_item_set,
                    ),
                )
                row_key = (
                    row.person_result_id,
                    row.segment_id,
                    row.local_person_id,
                    row.employee_id,
                    row.ocr_number,
                )
                unique_rows[row_key] = row

        all_rows = sorted(
            unique_rows.values(),
            key=lambda item: (item.segment_index, item.local_person_id or -1, item.person_result_id or -1),
        )

        filtered_rows = _apply_session_filters(all_rows, filters)
        status_ratio = {"정상": 0, "위반": 0, "미확인": 0}
        segment_violation_counts: dict[str, int] = {}

        for row in filtered_rows:
            status_ratio[row.overall_ppe_status] = (
                status_ratio.get(row.overall_ppe_status, 0) + 1
            )
            if row.overall_ppe_status == "위반":
                segment_violation_counts[row.segment_label] = (
                    segment_violation_counts.get(row.segment_label, 0) + 1
                )

        total_detected_people = len(all_rows)
        total_violation_people = sum(
            1 for row in all_rows if row.overall_ppe_status == "위반"
        )
        total_confirmed_people = sum(1 for row in all_rows if row.ocr_confirmed == "Y")

        return cls(
            session_id=session_id,
            total_segments=total_segments,
            total_detected_people=total_detected_people,
            total_violation_people=total_violation_people,
            total_confirmed_people=total_confirmed_people,
            rows=filtered_rows,
            status_ratio=status_ratio,
            segment_violation_counts=segment_violation_counts,
            source_segments=segments,
        )


def _apply_session_filters(rows: list[SessionPersonRowDto], filters: dict[str, str]):
    employee_keyword = (filters.get("employee_id") or "").strip().lower()
    ocr_keyword = (filters.get("ocr_number") or "").strip().lower()
    violation_type = filters.get("violation_type", "all")
    ocr_confirmed = filters.get("ocr_confirmed", "all")
    normal_included = filters.get("normal_included", "include")

    filtered_rows = []
    for row in rows:
        if employee_keyword and employee_keyword not in row.employee_id.lower():
            continue
        if ocr_keyword and ocr_keyword not in row.ocr_number.lower():
            continue
        if ocr_confirmed == "confirmed" and row.ocr_confirmed != "Y":
            continue
        if ocr_confirmed == "unconfirmed" and row.ocr_confirmed != "N":
            continue
        if normal_included == "violation_only" and row.overall_ppe_status != "위반":
            continue
        if violation_type == "helmet" and "헬멧" not in row.violation_type:
            continue
        if violation_type == "vest" and "조끼" not in row.violation_type:
            continue
        if violation_type == "any" and row.overall_ppe_status != "위반":
            continue
        filtered_rows.append(row)
    return filtered_rows
