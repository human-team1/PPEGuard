from typing import Dict, Any
from datetime import datetime
from app.domain.ports.detector_port import IDetector
from app.domain.entities.person import Person
from app.domain.rules import map_gear_to_person, evaluate_ppe_status


class AnalyzeWorker:
    """
    비즈니스 유스케이스 흐름 오케스트레이터
    - 웹캠: track 기반
    - 비디오 파일: predict 기반
    """

    def __init__(self, detector: IDetector):
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
        raw_persons, raw_vests, raw_helmets = self.detector.track(frame)
        return self._build_persons(frame, raw_persons, raw_vests, raw_helmets, keep_active=True)

    def run_inference_for_video(self, frame: Any) -> Dict[int, Person]:
        raw_persons, raw_vests, raw_helmets = self.detector.track(frame)
        return self._build_persons(frame, raw_persons, raw_vests, raw_helmets, keep_active=True)

    def _build_persons(
        self,
        frame: Any,
        raw_persons,
        raw_vests,
        raw_helmets,
        keep_active: bool,
    ) -> Dict[int, Person]:
        current_persons: Dict[int, Person] = {}

        for p_data in raw_persons:
            p_id = p_data["id"]

            if keep_active and p_id in self.active_persons:
                person = self.active_persons[p_id]
                person.bbox = p_data["bbox"]
                person.confidence = p_data["conf"]
            else:
                person = Person(
                    id=p_id,
                    bbox=p_data["bbox"],
                    confidence=p_data["conf"],
                )

            map_gear_to_person(person, raw_vests, raw_helmets)
            evaluate_ppe_status(person)

            h, w = frame.shape[:2]
            x1, y1, x2, y2 = person.bbox
            person.crop_image = frame[max(0, y1):min(h, y2), max(0, x1):min(w, x2)].copy()
            person.last_updated = datetime.now()

            current_persons[p_id] = person

        if keep_active:
            self.active_persons = current_persons
            return self.active_persons

        return current_persons
