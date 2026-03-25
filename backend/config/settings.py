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
    CUSTOMER_DB_DRIVER = os.getenv("CUSTOMER_DB_DRIVER", "mysql+pymysql")
    CUSTOMER_DB_HOST = os.getenv("CUSTOMER_DB_HOST", "")
    CUSTOMER_DB_PORT = os.getenv("CUSTOMER_DB_PORT", "3306")
    CUSTOMER_DB_NAME = os.getenv("CUSTOMER_DB_NAME", "")
    CUSTOMER_DB_USER = os.getenv("CUSTOMER_DB_USER", "")
    CUSTOMER_DB_PASSWORD = os.getenv("CUSTOMER_DB_PASSWORD", "")

    # OCR 설정
    EMPLOYEE_NO_REGEX = os.getenv("EMPLOYEE_NO_REGEX", "")
    EMPLOYEE_NO_MIN_LENGTH = int(os.getenv("EMPLOYEE_NO_MIN_LENGTH", "0"))
    EMPLOYEE_NO_MAX_LENGTH = int(os.getenv("EMPLOYEE_NO_MAX_LENGTH", "0"))
    OCR_INTERVAL_SEC = float(os.getenv("OCR_INTERVAL_SEC", "1"))

    @classmethod
    def get_customer_db_uri(cls):
        if not cls.CUSTOMER_DB_HOST or not cls.CUSTOMER_DB_NAME or not cls.CUSTOMER_DB_USER:
            raise ValueError("고객사 DB 연결 설정(CUSTOMER_DB_HOST, CUSTOMER_DB_NAME, CUSTOMER_DB_USER)이 누락되었습니다. .env 파일을 확인해 주세요.")
        
        return f"{cls.CUSTOMER_DB_DRIVER}://{cls.CUSTOMER_DB_USER}:{cls.CUSTOMER_DB_PASSWORD}@{cls.CUSTOMER_DB_HOST}:{cls.CUSTOMER_DB_PORT}/{cls.CUSTOMER_DB_NAME}"

    UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))
    FRAME_INTERVAL_SEC = float(os.getenv("FRAME_INTERVAL_SEC", "1"))

    YOLO_MODEL_PATH = os.getenv(
        "YOLO_MODEL_PATH",
        str(BASE_DIR / "app" / "infrastructure" / "ai_analyzer" / "models" / "best.pt"),
        # str(BASE_DIR / "app" / "infrastructure" / "ai_analyzer" / "models" / "yolo11s_ft_aug_best.pt"),
    )

    YOLO_TRACKER_CONFIG = os.getenv(
        "YOLO_TRACKER_CONFIG",
        str(BASE_DIR / "app" / "infrastructure" / "ai_analyzer" / "configs" / "bytetrack.yaml"),
    )


class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

def get_config():
    env = os.getenv("FLASK_ENV", "development")
    if env == "production":
        return ProductionConfig
    return DevelopmentConfig
