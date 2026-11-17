"""Flask application factory for the monitoring demo."""

from flask import Flask
from flask_wtf.csrf import CSRFProtect

from app.config import Config

csrf = CSRFProtect()


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError(
            "SECRET_KEY is not set. Export FLASK_SECRET_KEY or add "
            '"secret_key" to config.json (see .env.example / README).'
        )

    csrf.init_app(app)

    from app.routes import bp as main_bp

    app.register_blueprint(main_bp)

    @app.context_processor
    def inject_auth():
        from app.auth import current_username, is_authenticated

        return {
            "current_username": current_username(),
            "is_authenticated": is_authenticated(),
        }

    return app
