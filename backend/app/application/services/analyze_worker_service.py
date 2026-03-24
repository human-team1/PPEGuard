from typing import Dict, Any, List
from app.domain.ports.detector_port import IDetector
from app.domain.entities.person import Person
from app.domain.rules import map_gear_to_person, evaluate_ppe_status

class AnalyzeWorker:
    """
    비즈니스 유스케이스 흐름을 담당하는 오케스트레이터 (Application 계층)
    프레임 분석 -> 탐지 -> 매핑 -> 상태 판정의 흐름을 관리합니다.
    """
    
    def __init__(self, detector: IDetector):
        """
        추상화된 탐지기 포트(IDetector)를 주입받아 사용합니다. (DI)
        """
        self.detector = detector
        self.active_persons: Dict[int, Person] = {}

    def prepare_frame(self, image_base64: str) -> Any:
        """
        입력된 Base64 데이터를 모델 분석이 가능한 OpenCV 프레임으로 정규화합니다.
        (UserService의 .strip() 가공 로직과 유사한 역할)
        """
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]

        import base64
        import cv2
        import numpy as np
        
        img_bytes = base64.b64decode(image_base64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return frame

    def run_inference(self, frame: Any) -> Dict[int, Person]:
        """
        단일 프레임에 대한 분석 파이프라인을 실행합니다.

        1. AI 모델 실행 (Infrastructure 계층 호출 - YOLOv11)
        2. 탐지 데이터를 도메인 엔티티(Person)로 변환
        3. 도메인 규칙(map_gear, evaluate_status) 적용
        4. 추적 상태 반환
        """
        # 1. AI 모델을 통한 객체 탐지 및 추적 (Detector Port 활용)
        raw_persons, raw_vests, raw_helmets = self.detector.track(frame)
        
        current_frame_ids = []
        
        for p_data in raw_persons:
            p_id = p_data['id']
            current_frame_ids.append(p_id)
            
            # 2. 도메인 객체 관리 (생성 또는 업데이트)
            if p_id not in self.active_persons:
                person = Person(
                    id=p_id, 
                    bbox=p_data['bbox'], 
                    confidence=p_data['conf']
                )
                self.active_persons[p_id] = person
            else:
                person = self.active_persons[p_id]
                person.bbox = p_data['bbox']
                person.confidence = p_data['conf']

            # 3. 도메인 규칙(Business Logic) 적용
            # 장비 매핑 (조끼/헬멧 영역 매치)
            map_gear_to_person(person, raw_vests, raw_helmets)
            # 안전 상태 판정 및 위반 카운트 관리
            evaluate_ppe_status(person)

            # 4. 실시간 이미지 크롭 (OCR 용)
            h, w = frame.shape[:2]
            x1, y1, x2, y2 = person.bbox
            # ROI 경계 체크 (이미지 밖으로 나가지 않도록)
            person.crop_image = frame[max(0, y1):min(h, y2), max(0, x1):min(w, x2)].copy()

        # 5. 화면에서 사라진 객체는 관리 목록에서 제거 (메모리 정제)
        self.active_persons = {
            pid: p for pid, p in self.active_persons.items() 
            if pid in current_frame_ids
        }
        
        return self.active_persons
