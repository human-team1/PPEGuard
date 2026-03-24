def init_api(app):
    from .routes.health import health_bp
    from .routes.sessions import sessions_bp
    from .routes.results import results_bp
    from .routes.video import video_bp
    from .routes import sockets

    app.register_blueprint(health_bp)
    app.register_blueprint(sessions_bp)
    app.register_blueprint(results_bp)
    app.register_blueprint(video_bp)
