"""Описания параметров моделей на русском языке."""

PARAM_DESCRIPTIONS = {
    'model': 'Название модели для использования',
    'api_key': 'API ключ для доступа к сервису',
    'temperature': 'Температура генерации (0.0-2.0). Чем выше, тем более креативные ответы',
    'top_p': 'Top-p sampling (ядерная выборка). Альтернатива temperature',
    'seed': 'Случайное число для воспроизводимости результатов',
    'max_tokens': 'Максимальное количество токенов в ответе',
    'max_output_tokens': 'Максимальное количество токенов в ответе',
    'max_completion_tokens': 'Максимальное количество токенов в ответе',
    'frequency_penalty': 'Штраф за частоту (избегает повторений)',
    'reasoning_effort': 'Уровень усилий для рассуждений (low/medium/high)',
    'service_tier': 'Уровень сервиса (auto/default/flex/priority/scale)',
    'add_schema_to_system_prompt': 'Добавить JSON схему в системный промпт вместо использования response_format',
    'dont_force_structured_output': 'Не принуждать модель к структурированному выводу',
    'remove_min_items_from_schema': 'Удалить minItems из JSON схемы (для совместимости)',
    'remove_defaults_from_schema': 'Удалить значения по умолчанию из JSON схемы',
    'organization': 'ID организации OpenAI',
    'project': 'ID проекта',
    'base_url': 'Базовый URL API (для совместимых провайдеров)',
    'websocket_base_url': 'Базовый URL для WebSocket соединений',
    'timeout': 'Таймаут запроса в секундах',
    'max_retries': 'Максимальное количество повторов при ошибках',
    'default_headers': 'Заголовки HTTP по умолчанию',
    'default_query': 'Параметры запроса по умолчанию',
    'http_client': 'HTTP клиент для запросов',
    'reasoning_models': 'Список моделей с поддержкой рассуждений',
    'vertexai': 'Использовать Vertex AI вместо стандартного API',
    'credentials': 'Объект учетных данных Google',
    'location': 'Локация Google Cloud',
    'http_options': 'Опции HTTP для клиента',
    'include_system_in_user': 'Включить системные сообщения в первое пользовательское сообщение',
    'supports_structured_output': 'Использовать нативный JSON режим (True) или fallback через промпт (False)',
    'retryable_status_codes': 'HTTP коды статуса для повтора запроса',
    'retry_base_delay': 'Базовая задержка в секундах для экспоненциальной задержки',
    'retry_max_delay': 'Максимальная задержка в секундах между повторами',
    'thinking_budget': 'Бюджет размышлений для Gemini 2.5 (-1 для динамического, 0 отключает, или количество токенов)',
    'thinking_level': 'Уровень размышлений для Gemini 3 (minimal/low/medium/high)',
    'config': 'Дополнительные параметры конфигурации для generate_content',
    'auth_token': 'Токен аутентификации (альтернатива api_key)',
    'safe_prompt': 'Безопасный промпт (фильтрация контента)',
    'host': 'Адрес хоста Ollama (по умолчанию localhost:11434)',
    'client_params': 'Дополнительные параметры клиента',
    'ollama_options': 'Опции Ollama (temperature, top_p и др.)',
    'api_version': 'Версия API Azure OpenAI',
    'azure_endpoint': 'Конечная точка Azure OpenAI',
    'azure_deployment': 'Имя развертывания Azure',
    'azure_ad_token': 'Токен Azure AD',
    'azure_ad_token_provider': 'Провайдер токена Azure AD',
    'use_responses_api': 'Использовать Responses API вместо Chat Completions API',
    'model_id': 'OCID модели OCI GenAI',
    'service_endpoint': 'Конечная точка сервиса OCI',
    'compartment_id': 'OCID компартмента OCI',
    'provider': 'Провайдер модели (meta/cohere/xai)',
    'presence_penalty': 'Штраф за присутствие (только для Meta)',
    'top_k': 'Top-k sampling (для Cohere и xAI)',
    'auth_type': 'Тип аутентификации (например, API_KEY)',
    'auth_profile': 'Имя профиля аутентификации',
}

# Описания параметров для конкретных провайдеров (переопределяют общие)
MODEL_PARAM_DESCRIPTIONS = {}


def get_param_description(param_name: str, model_name: str = None) -> str:
    """Получить описание параметра на русском."""
    if model_name and model_name in MODEL_PARAM_DESCRIPTIONS:
        override = MODEL_PARAM_DESCRIPTIONS[model_name].get(param_name)
        if override:
            return override
    return PARAM_DESCRIPTIONS.get(param_name, f'Параметр {param_name}')
