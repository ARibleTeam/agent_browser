# agent_browser

Веб-интерфейс для [browser-use](https://github.com/browser-use/browser-use): задачи для AI-агента, который управляет Chromium. Один пользователь, выбор LLM в UI (OpenAI, Google, Anthropic, Ollama и др.), логи и скриншоты в реальном времени.

## Требования

- Python 3.11 или выше (3.12, 3.13, 3.14)
- [uv](https://github.com/astral-sh/uv) — быстрый менеджер пакетов Python

## Первая установка

### 1. Установите uv (если еще не установлен)

**Windows (PowerShell):**

```powershell
pip install uv
```

### 2. Установите зависимости проекта

```bash
python -m uv sync
```

### 3. Установите системные зависимости Playwright и Chromium


```powershell
python -m uv run python -m playwright install chromium
```

## Запуск

```bash
python -m uv run run.py
```

Откройте в браузере: **[http://localhost:5000](http://localhost:5000)**

## Переменные окружения

Переменные окружения (опционально):


| Переменная         | Описание                               |
| ------------------ | -------------------------------------- |
| `PORT`             | Порт приложения (по умолчанию 5000)    |
| `FLASK_HOST`       | Хост (по умолчанию 127.0.0.1)          |
| `FLASK_SECRET_KEY` | Секрет Flask (по умолчанию встроенный) |


Пример:

```bash
# Windows (PowerShell)
$env:PORT=8080; $env:FLASK_HOST="0.0.0.0"; python -m uv run python run.py
```

## Использование

1. **Модель** — выберите модель слева (ChatOpenAI, ChatGoogle, ChatOllama и др.).
2. **Настройка** — заполните обязательные параметры справа (`model`, `api_key` и т.д.).
3. **Проверка** — нажмите «Сохранить и проверить».
4. **Задача** — введите задачу в центре и нажмите «Отправить». Логи и скриншоты браузера появятся в интерфейсе.

## Поддерживаемые модели

ChatOpenAI, ChatGoogle, ChatAnthropic, ChatGroq, ChatMistral, ChatOllama, ChatAzureOpenAI, ChatVercel, ChatBrowserUse, ChatOCIRaw.

## Структура проекта

- `run.py` — точка входа
- `app/` — Flask: маршруты, API моделей/чата/браузера, запуск агента, CDP
- `pyproject.toml` — зависимости проекта (управляется через uv)
- `config/` — конфигурация моделей (API-ключи), создается автоматически при сохранении настроек в UI

## Конфигурация

Конфигурация моделей (API-ключи) сохраняется в `./config/models_config.json`. При первом запуске папка `config` создастся автоматически при сохранении настроек в UI.