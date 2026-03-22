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


def is_valid_worker_id(worker_id):
    """
    작업자 번호가 비어 있지 않고 숫자로만 이루어졌는지 확인한다.
    """
    if worker_id is None:
        return False

    worker_id = str(worker_id).strip()

    if worker_id == "":
        return False

    if not worker_id.isdigit():
        return False

    return True


def should_save_worker_id(confidence, threshold=0.7):
    """
    OCR confidence가 저장 기준 이상인지 판단한다.
    """
    if confidence is None:
        return False

    return confidence >= threshold