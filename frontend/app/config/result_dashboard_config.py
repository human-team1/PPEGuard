LIVE_MONITOR_CARD_DEFINITIONS = [
    {
        "key": "current_people",
        "label": "현재 인원",
        "accent": "#1565C0",
    },
    {
        "key": "current_violations",
        "label": "현재 위반 인원",
        "accent": "#C62828",
    },
    {
        "key": "current_violation_rate",
        "label": "현재 위반율",
        "accent": "#EF6C00",
    },
    {
        "key": "total_segments",
        "label": "총 세그먼트 수",
        "accent": "#6A1B9A",
    },
]

SESSION_CARD_DEFINITIONS = [
    {
        "key": "total_segments",
        "label": "총 세그먼트 수",
        "accent": "#1565C0",
        "description": "세션에 저장된 segment summary 개수",
    },
    {
        "key": "total_detected_people",
        "label": "세션 누적 감지 건수",
        "accent": "#2E7D32",
        "description": "세션의 모든 세그먼트 사람 결과 수",
    },
    {
        "key": "total_violation_people",
        "label": "세션 누적 위반 건수",
        "accent": "#C62828",
        "description": "헬멧 또는 조끼 상태가 위반인 사람 결과 수",
    },
    {
        "key": "total_confirmed_people",
        "label": "OCR 확정 건수",
        "accent": "#6A1B9A",
        "description": "ocr_confirmed 가 참인 사람 결과 수",
    },
]

SESSION_DASHBOARD_WIDGETS = [
    {"key": "total_segments", "label": "총 세그먼트 수 카드", "type": "metric"},
    {"key": "total_detected_people", "label": "세션 누적 감지 건수 카드", "type": "metric"},
    {"key": "total_violation_people", "label": "세션 누적 위반 건수 카드", "type": "metric"},
    {"key": "total_confirmed_people", "label": "OCR 확정 건수 카드", "type": "metric"},
    {"key": "status_ratio", "label": "상태별 비율 차트", "type": "chart"},
    {"key": "segment_violation_counts", "label": "세그먼트별 위반 수 차트", "type": "chart"},
]

SESSION_TABLE_COLUMNS = [
    {"key": "segment_label", "label": "구간", "default_visible": True},
    {"key": "reference_time", "label": "기준 시각", "default_visible": True},
    {"key": "employee_id", "label": "직원 ID", "default_visible": True},
    {"key": "ocr_number", "label": "OCR 번호", "default_visible": True},
    {"key": "ocr_confirmed", "label": "OCR 확정", "default_visible": True},
    {"key": "helmet_status", "label": "헬멧", "default_visible": True},
    {"key": "vest_status", "label": "조끼", "default_visible": True},
    {"key": "overall_ppe_status", "label": "종합 상태", "default_visible": True},
    {"key": "violation_type", "label": "위반 유형", "default_visible": True},
]

VIOLATION_FILTER_OPTIONS = [
    {"key": "all", "label": "전체"},
    {"key": "helmet", "label": "헬멧 미착용"},
    {"key": "vest", "label": "조끼 미착용"},
    {"key": "any", "label": "위반 있음"},
]

OCR_CONFIRMED_FILTER_OPTIONS = [
    {"key": "all", "label": "전체"},
    {"key": "confirmed", "label": "확정만"},
    {"key": "unconfirmed", "label": "미확정만"},
]

NORMAL_INCLUDED_FILTER_OPTIONS = [
    {"key": "include", "label": "정상 포함"},
    {"key": "violation_only", "label": "위반만"},
]

DASHBOARD_WIDGETS = SESSION_DASHBOARD_WIDGETS
TABLE_COLUMNS = SESSION_TABLE_COLUMNS
DEFAULT_PERIOD_KEY = "all"
