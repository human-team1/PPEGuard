from ..entities.detection_result import ItemWearStatus, OverallPPEStatus

def evaluate_ppe_status(
    helmet_status: ItemWearStatus, 
    vest_status: ItemWearStatus
) -> OverallPPEStatus:
    if helmet_status == ItemWearStatus.WEARING and vest_status == ItemWearStatus.WEARING:
        return OverallPPEStatus.COMPLIANT
    elif helmet_status == ItemWearStatus.NOT_WEARING or vest_status == ItemWearStatus.NOT_WEARING:
        return OverallPPEStatus.NON_COMPLIANT
    else:
        return OverallPPEStatus.UNKNOWN
