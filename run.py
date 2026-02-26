"""Точка входа: запуск приложения (локальное использование)."""
import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s [%(name)s] %(message)s')

from app import create_app
from app.config import Config

app = create_app()

if __name__ == '__main__':
    app.run(debug=False, host=Config.HOST, port=Config.PORT)
