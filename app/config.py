"""Конфигурация приложения (локальное использование одним пользователем)."""
import os


class Config:
    """Базовые настройки."""
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'local-browser-use-secret')
    PORT = int(os.environ.get('PORT', 5000))
    HOST = os.environ.get('FLASK_HOST', '127.0.0.1')
