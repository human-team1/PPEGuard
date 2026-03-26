from flask import Flask
from flask_socketio import SocketIO
from config.settings import get_config
from app.infrastructure.logging_config import configure_logging
from app.infrastructure.service_db.init_db import create_db_tables

# [가장 검증된 비동기 모드: eventlet]
# 웹소켓(WebSocket)과 HTTP 전송을 모두 지원하며, 윈도우에서 널리 쓰이는 표준 방식입니다.
socketio = SocketIO(
    cors_allowed_origins="*",
    async_mode='eventlet',
    logger=False,
    engineio_logger=False,
)

def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())
    configure_logging(app.config.get("LOG_LEVEL", "INFO"))
    create_db_tables()

    from app.presentation.api import init_api
    init_api(app)

    socketio.init_app(app)

    return app
