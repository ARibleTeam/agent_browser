"""Утилиты для работы с моделями browser_use (LLM)."""
import inspect
import json
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from app.utils.param_descriptions import get_param_description

from browser_use import (
    ChatAnthropic,
    ChatAzureOpenAI,
    ChatBrowserUse,
    ChatGoogle,
    ChatGroq,
    ChatMistral,
    ChatOllama,
    ChatOpenAI,
    ChatVercel,
)
try:
    from browser_use import ChatOCIRaw
    CHAT_OCI_RAW_AVAILABLE = True
except ImportError:
    ChatOCIRaw = None
    CHAT_OCI_RAW_AVAILABLE = False
from browser_use.llm.base import BaseChatModel
from browser_use.llm.exceptions import ModelProviderError, ModelRateLimitError
from browser_use.llm.messages import UserMessage

# Путь к конфигу: корень проекта (родитель app/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE = PROJECT_ROOT / 'config' / 'models_config.json'

# Системный промпт по умолчанию: всегда использовать Яндекс
DEFAULT_SYSTEM_PROMPT = "Всегда используй поисковую систему Яндекс."

MODEL_CLASSES: Dict[str, Type[BaseChatModel]] = {
    'ChatOpenAI': ChatOpenAI,
    'ChatGoogle': ChatGoogle,
    'ChatAnthropic': ChatAnthropic,
    'ChatGroq': ChatGroq,
    'ChatMistral': ChatMistral,
    'ChatOllama': ChatOllama,
    'ChatAzureOpenAI': ChatAzureOpenAI,
    'ChatVercel': ChatVercel,
    'ChatBrowserUse': ChatBrowserUse,
}
if CHAT_OCI_RAW_AVAILABLE and ChatOCIRaw is not None:
    MODEL_CLASSES['ChatOCIRaw'] = ChatOCIRaw

REQUIRED_PARAMS: Dict[str, List[str]] = {
    'ChatOpenAI': ['model', 'api_key'],
    'ChatGoogle': ['model', 'api_key'],
    'ChatAnthropic': ['model', 'api_key'],
    'ChatGroq': ['model', 'api_key'],
    'ChatMistral': ['model', 'api_key'],
    'ChatOllama': ['model'],
    'ChatAzureOpenAI': ['model', 'api_key'],
    'ChatVercel': ['model', 'api_key'],
    'ChatBrowserUse': ['model', 'api_key'],
}
if CHAT_OCI_RAW_AVAILABLE:
    REQUIRED_PARAMS['ChatOCIRaw'] = ['model_id', 'service_endpoint', 'compartment_id']


def get_model_class(model_name: str) -> Optional[Type[BaseChatModel]]:
    return MODEL_CLASSES.get(model_name)


def get_model_params_schema(model_name: str) -> Dict[str, Dict[str, Any]]:
    model_class = get_model_class(model_name)
    if not model_class:
        return {}
    if not is_dataclass(model_class):
        try:
            sig = inspect.signature(model_class.__init__)
            schema = {}
            for param_name, param in sig.parameters.items():
                if param_name == 'self' or param_name.startswith('_'):
                    continue
                field_info = {
                    'type': str(param.annotation) if param.annotation != inspect.Parameter.empty else 'Any',
                    'default': param.default if param.default != inspect.Parameter.empty else None,
                    'required': param.default == inspect.Parameter.empty,
                    'description': get_param_description(param_name, model_name),
                }
                type_str = str(field_info['type'])
                field_info['form_type'] = 'number' if 'int' in type_str or 'float' in type_str else 'checkbox' if 'bool' in type_str else 'text'
                schema[param_name] = field_info
            return schema
        except Exception:
            return {}
    schema = {}
    for field in fields(model_class):
        if field.name.startswith('_'):
            continue
        default_value = None
        has_default_factory = False
        if field.default != inspect.Parameter.empty:
            default_value = field.default
        elif field.default_factory != inspect.Parameter.empty:
            has_default_factory = True
        field_info = {
            'type': str(field.type),
            'default': default_value,
            'has_default_factory': has_default_factory,
            'required': field.default == inspect.Parameter.empty and field.default_factory == inspect.Parameter.empty,
            'description': get_param_description(field.name, model_name),
        }
        type_str = str(field_info['type'])
        field_info['form_type'] = 'number' if 'int' in type_str or 'float' in type_str else 'checkbox' if 'bool' in type_str else 'text'
        schema[field.name] = field_info
    return schema


def validate_model_config(model_name: str, config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    required = REQUIRED_PARAMS.get(model_name, [])
    missing = [p for p in required if not config.get(p)]
    if missing:
        return False, f"Отсутствуют обязательные параметры: {', '.join(missing)}"
    return True, None


def create_model_instance(model_name: str, config: Dict[str, Any]) -> BaseChatModel:
    model_class = get_model_class(model_name)
    if not model_class:
        raise ValueError(f"Неизвестная модель: {model_name}")
    is_valid, error = validate_model_config(model_name, config)
    if not is_valid:
        raise ValueError(error)
    filtered_config = {
        k: v for k, v in config.items()
        if not k.startswith('_') and v is not None and v != ''
    }
    try:
        return model_class(**filtered_config)
    except Exception as e:
        raise ValueError(f"Ошибка создания модели: {str(e)}")


def format_error_message(e: Exception) -> str:
    error_msg = str(e)
    if isinstance(e, ModelProviderError):
        status_code = getattr(e, 'status_code', None)
        if status_code == 404:
            return "Модель или endpoint не найдены. Проверьте правильность названия модели и URL."
        if status_code == 401:
            return "Неверный API ключ. Проверьте правильность ключа."
        if status_code == 403:
            return "Доступ запрещён. Проверьте права доступа API ключа."
        if status_code == 429:
            return "Превышен лимит запросов. Попробуйте позже."
        if status_code == 500:
            return "Ошибка сервера провайдера. Попробуйте позже."
        if status_code:
            return f"Ошибка HTTP {status_code}: {error_msg}"
        return error_msg
    if isinstance(e, ModelRateLimitError):
        return f"Превышен лимит запросов. Попробуйте позже: {error_msg}"
    if "404" in error_msg or "Not Found" in error_msg:
        return "Модель или endpoint не найдены. Проверьте правильность названия модели."
    if "401" in error_msg or "Unauthorized" in error_msg or "Invalid API key" in error_msg:
        return "Неверный API ключ. Проверьте правильность ключа."
    if "403" in error_msg or "Forbidden" in error_msg:
        return "Доступ запрещён. Проверьте права доступа API ключа."
    if "429" in error_msg or "rate limit" in error_msg.lower():
        return "Превышен лимит запросов. Попробуйте позже."
    if "timeout" in error_msg.lower() or "connection" in error_msg.lower():
        return f"Ошибка подключения: {error_msg}"
    if "ssl" in error_msg.lower() or "certificate" in error_msg.lower() or "certificate_verify_failed" in error_msg:
        return f"Ошибка SSL: {error_msg}"
    return error_msg


async def test_model_connection(model_instance: BaseChatModel) -> tuple[bool, Optional[str]]:
    try:
        result = await model_instance.ainvoke([UserMessage(content="Привет")])
        if result and result.completion:
            return True, None
        return False, "Модель вернула пустой ответ"
    except Exception as e:
        return False, format_error_message(e)


def load_model_configs() -> Dict[str, Dict[str, Any]]:
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_model_config(model_name: str, config: Dict[str, Any]) -> None:
    configs = load_model_configs()
    configs[model_name] = config
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(configs, f, indent=2, ensure_ascii=False)


def get_model_config(model_name: str) -> Optional[Dict[str, Any]]:
    return load_model_configs().get(model_name)
