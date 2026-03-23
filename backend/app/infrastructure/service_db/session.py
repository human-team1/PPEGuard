from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import get_config

config = get_config()
service_db_uri = config.SERVICE_DATABASE_URI
engine = create_engine(service_db_uri, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
