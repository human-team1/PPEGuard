import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    BASE_DIR = Path(__file__).resolve().parent.parent

    # 우리 서비스 전용 DB
    SERVICE_DATABASE_URI = os.getenv(
        "SERVICE_DATABASE_URI",
        "sqlite:///./ppe_guard.db",
    )

    # 고객사 사내망 DB
    CUSTOMER_DB_DRIVER = os.getenv("CUSTOMER_DB_DRIVER", "")
    CUSTOMER_DB_HOST = os.getenv("CUSTOMER_DB_HOST", "")
    CUSTOMER_DB_PORT = os.getenv("CUSTOMER_DB_PORT", "")
    CUSTOMER_DB_NAME = os.getenv("CUSTOMER_DB_NAME", "")
    CUSTOMER_DB_USER = os.getenv("CUSTOMER_DB_USER", "")
    CUSTOMER_DB_PASSWORD = os.getenv("CUSTOMER_DB_PASSWORD", "")

    UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))
    AI_DETECTOR_PROVIDER = os.getenv("AI_DETECTOR_PROVIDER", "mock")
    AI_OCR_PROVIDER = os.getenv("AI_OCR_PROVIDER", "mock")
    FRAME_INTERVAL_SEC = int(os.getenv("FRAME_INTERVAL_SEC", "3"))

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

def get_config():
    env = os.getenv("FLASK_ENV", "development")
    if env == "production":
        return ProductionConfig
    return DevelopmentConfig