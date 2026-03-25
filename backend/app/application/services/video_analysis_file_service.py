import os
import uuid

import cv2


class VideoAnalysisFileService:
    def __init__(self, upload_dir: str, crop_dir: str):
        self.upload_dir = upload_dir
        self.crop_dir = crop_dir

        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.crop_dir, exist_ok=True)

    def save_video_file(self, video_file, ext: str) -> str:
        saved_name = f"{uuid.uuid4().hex}{ext}"
        saved_path = os.path.join(self.upload_dir, saved_name)
        video_file.save(saved_path)
        return saved_path

    def save_crop_image(self, session_id: str, frame_no: int, person_index: int, crop_image):
        if crop_image is None:
            return None

        if getattr(crop_image, "size", 0) == 0:
            return None

        filename = f"{session_id}_f{frame_no}_p{person_index}.jpg"
        saved_path = os.path.join(self.crop_dir, filename)
        cv2.imwrite(saved_path, crop_image)
        return saved_path

    def save_segment_frame(self, session_id: str, segment_index: int, frame_no: int, frame_image):
        if frame_image is None:
            return None

        if getattr(frame_image, "size", 0) == 0:
            return None

        filename = f"{session_id}_segment{segment_index}_f{frame_no}.jpg"
        saved_path = os.path.join(self.crop_dir, filename)
        cv2.imwrite(saved_path, frame_image)
        return saved_path

    def delete_file(self, path: str | None) -> None:
        if not path:
            return

        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as exc:
                print(f"[VideoAnalysis] 파일 삭제 실패 - path={path}, error={exc}")

    def cleanup_previous_minute_frames(self, minute_frame_store: dict, target_minute_bucket: int) -> None:
        candidates = minute_frame_store.get(target_minute_bucket, [])
        if not candidates:
            return

        best = max(candidates, key=lambda item: item["score"])

        for item in candidates:
            path = item["path"]
            if path == best["path"]:
                continue

            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as exc:
                    print(f"[VideoAnalysis] OCR crop 삭제 실패 - path={path}, error={exc}")

        minute_frame_store.pop(target_minute_bucket, None)
