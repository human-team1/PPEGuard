from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import get_config

config = get_config()

try:
    customer_db_uri = config.get_customer_db_uri()
    customer_engine = create_engine(customer_db_uri, echo=False)
    CustomerSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=customer_engine)
except ValueError:
    # 환경변수 누락 시, 구동은 되게 하되 실제 저장 시도 시 연결이 없어 실패하도록 빈 세션 팩토리 생성 가능
    # 본 요구사항에서는 DB 설정이 누락되어있어도 예외처리만 하면 됨
    customer_engine = None
    CustomerSessionLocal = None
