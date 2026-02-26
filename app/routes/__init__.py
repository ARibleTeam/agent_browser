"""Регистрация blueprints."""
from flask import Flask

from app.routes.api_browser import api_browser_bp
from app.routes.api_chat import api_chat_bp
from app.routes.api_models import api_models_bp
from app.routes.pages import pages_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_models_bp)
    app.register_blueprint(api_chat_bp)
    app.register_blueprint(api_browser_bp)
