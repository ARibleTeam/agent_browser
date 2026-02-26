"""Application factory: создание Flask-приложения."""
from flask import Flask

from app.config import Config
from app.routes import register_blueprints


def create_app(config_object: type = Config) -> Flask:
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object(config_object)
    register_blueprints(app)
    return app
