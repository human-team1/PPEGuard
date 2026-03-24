from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple

class IDetector(ABC):
    """AI 모델(YOLO 등)에 대한 추상화 인터페이스 (Domain Port)"""
    
    @abstractmethod
    def track(self, frame: Any, conf: float = 0.5) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        프레임으로부터 사람, 조끼, 헬멧의 추적/탐지 결과를 반환

        Returns:
            persons (List[Dict]): {id, bbox, conf} 형태
            vests (List[Dict]): {bbox, conf} 형태
            helmets (List[Dict]): {bbox, conf} 형태
        """
        pass

    @abstractmethod
    def detect(
        self,
        frame: Any,
        conf: float = 0.5
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        동영상 파일 프레임 분석용 탐지 기반 분석
        Returns:
            persons: {id, bbox, conf}
            vests: {bbox, conf}
            helmets: {bbox, conf}
        """
        pass
    @abstractmethod
    def get_names(self) -> Dict[int, str]:
        """모델의 클래스 이름 딕셔너리 반환 (예: {0: 'person', 1: 'vest', ...})"""
        pass

