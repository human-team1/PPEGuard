def init_api(app):
    from .routes.health import health_bp
    from .routes.sessions import sessions_bp
    from .routes.results import results_bp
    
    app.register_blueprint(health_bp)
    app.register_blueprint(sessions_bp)
    app.register_blueprint(results_bp)

    # [추가/변경: WebSocket 핸들러 임포팅]
    # HTTP Blueprint 외에 별도의 소켓 네임스페이스 및 핸들러 등록을 위해 사용
    from .routes import sockets
