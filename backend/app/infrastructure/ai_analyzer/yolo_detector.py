import torch
import functools
import os
from typing import List, Dict, Any, Tuple
from ultralytics import YOLO
from app.domain.ports.detector_port import IDetector


class YoloDetector(IDetector):
    """
    YOLO 기반 객체 탐지/추적 구현체
    - 웹캠: track()
    - 동영상 파일: detect()
    """

    def __init__(self, model_path: str, tracker_config: str):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {model_path}")

        if not os.path.exists(tracker_config):
            raise FileNotFoundError(f"트래커 설정 파일을 찾을 수 없습니다: {tracker_config}")

        _orig_load = torch.load
        torch.load = functools.partial(_orig_load, weights_only=False)
        try:
            self.model = YOLO(model_path)
        finally:
            torch.load = _orig_load

        self.tracker_config = tracker_config

    def track(
        self,
        frame: Any,
        conf: float = 0.5
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        results = self.model.track(
            frame,
            persist=True,
            conf=conf,
            tracker=self.tracker_config,
            verbose=False
        )
        return self._parse_results(results, use_tracking=True)

    def detect(
        self,
        frame: Any,
        conf: float = 0.5
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        results = self.model.predict(
            frame,
            conf=conf,
            verbose=False
        )
        return self._parse_results(results, use_tracking=False)

    def _parse_results(
        self,
        results,
        use_tracking: bool
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        persons = []
        vests = []
        helmets = []

        if results and results[0].boxes is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
            clss = results[0].boxes.cls.cpu().numpy().astype(int)
            confs = results[0].boxes.conf.cpu().numpy()

            ids = None
            if use_tracking and results[0].boxes.id is not None:
                ids = results[0].boxes.id.cpu().numpy().astype(int)

            person_seq = 1

            for idx, (box, cls, conf_val) in enumerate(zip(boxes, clss, confs)):
                label = self.model.names[int(cls)].lower()

                res_data = {
                    "bbox": box.tolist(),
                    "conf": float(conf_val),
                }

                if label == "person":
                    if use_tracking and ids is not None:
                        res_data["id"] = int(ids[idx])
                    else:
                        res_data["id"] = person_seq
                        person_seq += 1
                    persons.append(res_data)

                elif label == "vest":
                    vests.append(res_data)

                elif label == "helmet":
                    helmets.append(res_data)

        return persons, vests, helmets

    def get_names(self) -> Dict[int, str]:
        return self.model.names
        
