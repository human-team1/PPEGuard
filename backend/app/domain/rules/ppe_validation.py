from app.domain.entities.person import Person

def evaluate_ppe_status(person: Person):
    """
    최종 안전 상태 판정 및 위반 카운트 관리 규칙
    (조끼와 헬멧 모두 착용해야 SAFE로 판정)
    """
    if not person.is_safe():
        person.violation_count += 1
    else:
        # 안전 확보 시 카운트 리셋 (또는 로직에 따라 점진적 감소 가능)
        person.violation_count = 0
