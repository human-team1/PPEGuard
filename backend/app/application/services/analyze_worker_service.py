from typing import Dict, Any
from app.domain.ports.detector_port import IDetector
from app.domain.entities.person import Person
from app.domain.rules import map_gear_to_person, evaluate_ppe_status


class AnalyzeWorker:
    """
    비즈니스 유스케이스 흐름 오케스트레이터
    - run_inference(): 웹캠용 track
    - run_inference_for_video(): 동영상용 detect
    """

    def __init__(self, detector: IDetector):
        self.detector = detector
        self.active_persons: Dict[int, Person] = {}

    def run_inference(self, frame: Any) -> Dict[int, Person]:
        raw_persons, raw_vests, raw_helmets = self.detector.track(frame)
        return self._build_persons(frame, raw_persons, raw_vests, raw_helmets, keep_active=True)

    def run_inference_for_video(self, frame: Any) -> Dict[int, Person]:
        raw_persons, raw_vests, raw_helmets = self.detector.detect(frame)
        return self._build_persons(frame, raw_persons, raw_vests, raw_helmets, keep_active=False)

    def _build_persons(
        self,
        frame: Any,
        raw_persons,
        raw_vests,
        raw_helmets,
        keep_active: bool,
    ) -> Dict[int, Person]:
        current_persons: Dict[int, Person] = {}
        current_frame_ids = []

        for p_data in raw_persons:
            p_id = p_data["id"]
            current_frame_ids.append(p_id)

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

            current_persons[p_id] = person

        if keep_active:
            self.active_persons = {
                pid: p for pid, p in current_persons.items()
                if pid in current_frame_ids
            }
            return self.active_persons

        return current_persons