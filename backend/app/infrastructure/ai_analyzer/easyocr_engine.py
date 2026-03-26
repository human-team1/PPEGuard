import logging
import math
import re

import cv2
import easyocr

from app.domain.ports.ocr_port import OCRPort


logger = logging.getLogger(__name__)


class EasyOCREngine(OCRPort):
    def __init__(
        self,
        languages=None,
        gpu=False,
        min_confidence=0.2,
        min_length=1,
        max_length=4,
    ):
        self.languages = languages or ["en"]
        self.gpu = gpu
        self.min_confidence = min_confidence
        self.min_length = min_length
        self.max_length = max_length
        self.reader = easyocr.Reader(self.languages, gpu=self.gpu)

    def extract_worker_id(self, image):
        result = self.recognize(image)
        best = result.get("best_candidate")

        if not best:
            return None

        return {
            "worker_id": best["cleaned_text"],
            "confidence": best["confidence"],
            "raw_text": best["raw_text"],
            "cleaned_text": best["cleaned_text"],
        }

    def recognize(self, image):
        if image is None:
            return {"raw_results": [], "best_candidate": None}

        if not hasattr(image, "shape"):
            return {"raw_results": [], "best_candidate": None}

        if image.size == 0:
            return {"raw_results": [], "best_candidate": None}

        preprocessed = self.preprocess(image)
        parsed = self.run_easyocr(preprocessed)
        best = self.select_best_candidate(parsed)

        return {
            "raw_results": parsed,
            "best_candidate": best,
        }

    def preprocess(self, image_bgr):
        return cv2.resize(
            image_bgr,
            None,
            fx=2,
            fy=2,
            interpolation=cv2.INTER_CUBIC,
        )

    def run_easyocr(self, image):
        try:
            results = self.reader.readtext(image, detail=1)
            parsed = []

            for bbox, text, conf in results:
                cleaned = self.clean_text(text)

                parsed.append(
                    {
                        "raw_text": str(text),
                        "cleaned_text": cleaned,
                        "confidence": float(conf),
                        "angle": self.get_angle_from_bbox(bbox),
                        "bbox": bbox,
                    }
                )

            return parsed

        except Exception:
            logger.exception("[OCR] easyocr execution failed")
            return []

    def select_best_candidate(self, parsed):
        valid = [
            x
            for x in parsed
            if x["cleaned_text"] != ""
            and self.min_length <= len(x["cleaned_text"]) <= self.max_length
            and x["confidence"] >= self.min_confidence
        ]

        if not valid:
            return None

        return max(valid, key=lambda x: x["confidence"])

    def clean_text(self, text):
        text = str(text).upper()

        replacements = {
            "O": "0",
            "I": "1",
            "L": "1",
            "S": "5",
            "B": "8",
            "Z": "2",
        }

        for src, dst in replacements.items():
            text = text.replace(src, dst)

        text = re.sub(r"[^0-9]", "", text)
        return text

    def get_angle_from_bbox(self, bbox):
        try:
            (x1, y1), (x2, y2), _, _ = bbox
            angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
            return round(angle, 2)
        except Exception:
            return None
