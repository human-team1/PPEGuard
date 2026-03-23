from flask import Flask
from config.settings import get_config

def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())

    from app.presentation.api import init_api
    init_api(app)

    return app 