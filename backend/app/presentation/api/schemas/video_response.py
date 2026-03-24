from dataclasses import dataclass
from typing import Optional


@dataclass
class VideoUploadResponse:
    success: bool
    session_id: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None
    error: Optional[dict] = None

    def to_dict(self) -> dict:
        result = {
            "success": self.success,
            "session_id": self.session_id,
            "status": self.status,
            "message": self.message,
            "error": self.error,
        }
        return {k: v for k, v in result.items() if v is not None}