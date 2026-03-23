from app.domain.entities.person import Person
from app.domain.entities.detection_result import OverallPPEStatus, ItemWearStatus

# 최종 안전 상태 판정 및 위반 카운트 관리 규칙(조끼와 헬멧 모두 착용해야 SAFE로 판정)입니다. 
def evaluate_ppe_status(person: Person):
    if not person.is_safe():
        person.violation_count += 1
    else:
        # 안전 확보 시 카운트 리셋 (또는 로직에 따라 점진적 감소 가능)
        person.violation_count = 0


# 헬멧/조끼 착용 상태를 기반으로 최종 PPE 상태를 계산합니다. 
def get_overall_ppe_status(helmet_status, vest_status):
    if (
        helmet_status == ItemWearStatus.WEARING
        and vest_status == ItemWearStatus.WEARING
    ):
        return OverallPPEStatus.COMPLIANT

    if (
        helmet_status == ItemWearStatus.NOT_WEARING
        or vest_status == ItemWearStatus.NOT_WEARING
    ):
        return OverallPPEStatus.NON_COMPLIANT

    return OverallPPEStatus.UNKNOWN


# 작업자 번호가 비어 있지 않고 숫자로만 이루어졌는지 확인한다.
def is_valid_worker_id(worker_id):
    if worker_id is None:
        return False

    worker_id = str(worker_id).strip()

    if worker_id == "":
        return False

    if not worker_id.isdigit():
        return False

    return True

#  OCR confidence가 저장 기준(신뢰도 70) 이상인지 판단한다.
def should_save_worker_id(confidence, threshold=0.7):
    if confidence is None:
        return False

    return confidence >= threshold