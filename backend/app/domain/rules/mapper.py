from typing import List, Dict, Any
from app.domain.entities.person import Person

def map_gear_to_person(person: Person, raw_vests: List[Dict[str, Any]], raw_helmets: List[Dict[str, Any]]):
    """
    탐지된 단일 장비(조끼/헬멧)들을 한 명의 사람 객체의 바운딩 박스 내부에 매핑

    Args:
        person (Person): 탐지된 사람 엔티티
        raw_vests (List[Dict]): 전체 조끼 탐지 결과 (bbox, conf 포함)
        raw_helmets (List[Dict]): 전체 헬멧 탐지 결과 (bbox, conf 포함)
    """
    px1, py1, px2, py2 = person.bbox
    
    # 조끼 매핑 (장비 박스의 중심점이 사람 박스 내부에 있는지 확인)
    for v in raw_vests:
        vb = v['bbox']
        vx_c, vy_c = (vb[0] + vb[2]) / 2, (vb[1] + vb[3]) / 2
        
        if px1 < vx_c < px2 and py1 < vy_c < py2:
            person.has_vest = True
            person.vest_bbox = vb
            person.vest_confidence = v['conf']
            break
            
    # 헬멧 매핑
    for h in raw_helmets:
        hb = h['bbox']
        hx_c, hy_c = (hb[0] + hb[2]) / 2, (hb[1] + hb[3]) / 2
        
        if px1 < hx_c < px2 and py1 < hy_c < py2:
            person.has_helmet = True
            person.helmet_bbox = hb
            person.helmet_confidence = h['conf']
            break
