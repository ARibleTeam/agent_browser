"""API: модели (список, схема, конфиг, тест)."""
import asyncio
import json
import logging

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

from app.utils.models import (
    MODEL_CLASSES,
    REQUIRED_PARAMS,
    DEFAULT_SYSTEM_PROMPT,
    create_model_instance,
    get_model_config,
    get_model_params_schema,
    save_model_config,
    test_model_connection,
)

api_models_bp = Blueprint('api_models', __name__, url_prefix='/api')


@api_models_bp.route('/models')
def get_available_models():
    return jsonify({'success': True, 'models': list(MODEL_CLASSES.keys())})


@api_models_bp.route('/models/<model_name>/schema')
def get_model_schema(model_name: str):
    try:
        schema = get_model_params_schema(model_name)
        required = REQUIRED_PARAMS.get(model_name, [])
        cleaned_schema = {}
        for key, value in schema.items():
            cleaned_value = {}
            for k, v in value.items():
                try:
                    json.dumps(v)
                    cleaned_value[k] = v
                except (TypeError, ValueError):
                    pass
            cleaned_schema[key] = cleaned_value
        return jsonify({'success': True, 'schema': cleaned_schema, 'required': required})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@api_models_bp.route('/models/<model_name>/config', methods=['GET'])
def get_config(model_name: str):
    try:
        config = get_model_config(model_name)
        config_dict = config or {}
        is_verified = config_dict.get('_verified', False)

        # Системный промпт храним как служебное поле, но показываем в форме как обычный параметр
        system_prompt_value = config_dict.get('_system_prompt', DEFAULT_SYSTEM_PROMPT)

        config_for_form = {k: v for k, v in config_dict.items() if not k.startswith('_')}
        config_for_form['system_prompt'] = system_prompt_value

        return jsonify({
            'success': True,
            'config': config_for_form,
            'verified': is_verified,
            'system_prompt_default': DEFAULT_SYSTEM_PROMPT,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@api_models_bp.route('/models/<model_name>/config', methods=['POST'])
def save_config(model_name: str):
    try:
        config = request.get_json()
        if not config:
            return jsonify({'success': False, 'error': 'Конфигурация не предоставлена'}), 400

        # Вынести системный промпт в служебное поле, чтобы не передавать его в конструктор модели
        system_prompt = config.pop('system_prompt', None)
        if system_prompt is not None and system_prompt != '':
            config['_system_prompt'] = system_prompt
        else:
            # Если поле пустое — используем дефолтный промпт
            config['_system_prompt'] = DEFAULT_SYSTEM_PROMPT

        save_model_config(model_name, config)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@api_models_bp.route('/models/<model_name>/test', methods=['POST'])
def test_model(model_name: str):
    try:
        config = request.get_json()
        if not config:
            logger.warning("[test %s] Конфигурация не предоставлена", model_name)
            return jsonify({'success': False, 'error': 'Конфигурация не предоставлена'}), 400

        # Обработка системного промпта: не передавать его в конструктор модели
        system_prompt = config.pop('system_prompt', None)
        if system_prompt is not None and system_prompt != '':
            config['_system_prompt'] = system_prompt
        else:
            # Если поле пустое — используем дефолтный промпт
            config['_system_prompt'] = DEFAULT_SYSTEM_PROMPT

        model_instance = create_model_instance(model_name, config)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success, error = loop.run_until_complete(test_model_connection(model_instance))
        loop.close()
        if success:
            config['_verified'] = True
            save_model_config(model_name, config)
            return jsonify({'success': True, 'message': 'Подключение успешно установлено'})
        logger.warning("[test %s] Ошибка подключения: %s", model_name, error)
        return jsonify({'success': False, 'error': error or 'Неизвестная ошибка'}), 400
    except Exception as e:
        from app.utils.models import format_error_message
        err_msg = format_error_message(e)
        logger.exception("[test %s] Исключение: %s", model_name, err_msg)
        return jsonify({'success': False, 'error': err_msg}), 400
