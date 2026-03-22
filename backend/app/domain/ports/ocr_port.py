from abc import ABC, abstractmethod

class OCRPort(ABC):
    @abstractmethod
    def extract_worker_id(self, image):
        """
        크롭된 조끼 이미지에서 OCR 결과를 반환합니다.
        반환 형식:
        {
            "worker_id": "106",
            "confidence": 0.82,
            "raw_text": "106",
            "cleaned_text": "106"
        }
        실패하면 None 반환
        """
        raise NotImplementedError