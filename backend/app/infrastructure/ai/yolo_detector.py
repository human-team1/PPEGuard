import torch
import functools
import os
from typing import List, Dict, Any, Tuple
from ultralytics import YOLO
from app.domain.ports.detector_port import IDetector

class YoloDetector(IDetector):
    """
    YOLOv11 기반의 객체 탐지 및 추적 구현체 (Infrastructure 계층)
    """
    
    def __init__(self, model_path: str, tracker_config: str):
        """
        Args:
            model_path (str): .pt 모델 가중치 파일 경로
            tracker_config (str): .yaml 트래커 설정 파일 경로
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {model_path}")
            
        # PyTorch 2.6+ 보안 정책(weights_only) 대응을 위한 임시 패치
        _orig_load = torch.load
        torch.load = functools.partial(_orig_load, weights_only=False)
        try:
            self.model = YOLO(model_path)
        finally:
            torch.load = _orig_load
            
        self.tracker_config = tracker_config

    def track(self, frame: Any, conf: float = 0.5) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        프레임 분석 및 결과 파싱 (사람, 조끼, 헬멧 분류)
        """
        results = self.model.track(
            frame, 
            persist=True, 
            conf=conf, 
            tracker=self.tracker_config, 
            verbose=False
        )
        
        persons = []
        vests = []
        helmets = []
        
        if results and results[0].boxes is not None:
            # 추적 ID가 있는 경우에만 처리 (아이디가 없는 탐지 결과는 무시하거나 별도 처리 가능)
            boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
            clss = results[0].boxes.cls.cpu().numpy().astype(int)
            confs = results[0].boxes.conf.cpu().numpy()
            
            # ID 추출 (id가 None인 경우를 대비)
            ids = results[0].boxes.id
            ids = ids.cpu().numpy().astype(int) if ids is not None else [None] * len(boxes)
            
            for box, obj_id, cls, conf_val in zip(boxes, ids, clss, confs):
                label = self.model.names[int(cls)].lower()
                
                res_data = {
                    'bbox': box.tolist(),
                    'conf': float(conf_val)
                }
                
                if label == 'person' and obj_id is not None:
                    res_data['id'] = int(obj_id)
                    persons.append(res_data)
                elif label == 'vest':
                    vests.append(res_data)
                elif label == 'helmet':
                    helmets.append(res_data)
        
        return persons, vests, helmets

    def get_names(self) -> Dict[int, str]:
        """클래스 맵 반환"""
        return self.model.names
