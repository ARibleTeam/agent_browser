"""API: чат (запуск агента, остановка)."""
import json
import multiprocessing
import queue

from flask import Blueprint, Response, jsonify, request, stream_with_context

import app.state as state
from app.services.agent_runner import run_agent_process, stop_current_agent_process
from app.utils.models import format_error_message, get_model_config

api_chat_bp = Blueprint('api_chat', __name__, url_prefix='/api')


@api_chat_bp.route('/chat', methods=['POST'])
def send_message():
    try:
        data = request.get_json()
        model_name = data.get('model')
        task = data.get('message')
        if not model_name or not task:
            return jsonify({'success': False, 'error': 'Модель и сообщение обязательны'}), 400
        config = get_model_config(model_name)
        if not config:
            return jsonify({'success': False, 'error': 'Модель не настроена'}), 400
        stop_current_agent_process()
        state.current_browser_info = None
        state.agent_log_queue = multiprocessing.Queue()
        state.current_agent_process = multiprocessing.Process(
            target=run_agent_process,
            args=(state.agent_log_queue, model_name, config, task)
        )
        state.current_agent_process.start()

        def generate():
            try:
                result_received = False
                while not result_received:
                    try:
                        log_data = state.agent_log_queue.get(timeout=0.5)
                    except (queue.Empty, OSError):
                        # Процесс завершился без отправки result — не зависаем
                        if (
                            state.current_agent_process
                            and not state.current_agent_process.is_alive()
                        ):
                            log_data = {
                                'type': 'result',
                                'success': False,
                                'error': 'Агент неожиданно завершился',
                            }
                        else:
                            yield ": keep-alive\n\n"
                            continue
                    if not isinstance(log_data, dict) or 'type' not in log_data:
                        continue
                    if log_data['type'] == 'browser_info':
                        state.current_browser_info = log_data
                    try:
                        payload = json.dumps(log_data, ensure_ascii=False)
                    except (TypeError, ValueError):
                        continue
                    yield f"data: {payload}\n\n"
                    if log_data.get('type') == 'result' and 'success' in log_data:
                        result_received = True
                        state.current_browser_info = None
                if state.current_agent_process:
                    state.current_agent_process.join(timeout=1)
            except Exception as e:
                state.current_browser_info = None
                yield f"data: {json.dumps({'type': 'result', 'success': False, 'error': format_error_message(e)}, ensure_ascii=False)}\n\n"
        return Response(stream_with_context(generate()), mimetype='text/event-stream')
    except Exception as e:
        return jsonify({'success': False, 'error': format_error_message(e)}), 400


@api_chat_bp.route('/chat/stop', methods=['POST'])
def stop_agent():
    try:
        stop_current_agent_process()
        state.current_browser_info = None
        return jsonify({'success': True, 'message': 'Выполнение остановлено'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
