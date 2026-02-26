"""API: скриншоты браузера (CDP)."""
import asyncio
import json
import time

from flask import Blueprint, Response, jsonify, stream_with_context

import app.state as state
from app.services.browser_cdp import get_screenshot_via_cdp

api_browser_bp = Blueprint('api_browser', __name__, url_prefix='/api')


@api_browser_bp.route('/browser/screenshot', methods=['GET'])
def get_browser_screenshot():
    try:
        if not state.current_browser_info or 'cdp_endpoint' not in state.current_browser_info:
            return jsonify({'success': False, 'error': 'Браузер не запущен'}), 404
        cdp_endpoint = state.current_browser_info['cdp_endpoint']
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            screenshot_data = loop.run_until_complete(get_screenshot_via_cdp(cdp_endpoint))
        finally:
            loop.close()
        if screenshot_data:
            return jsonify({'success': True, 'screenshot': screenshot_data})
        return jsonify({'success': False, 'error': 'Не удалось получить скриншот'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_browser_bp.route('/browser/screenshot/stream', methods=['GET'])
def stream_browser_screenshot():
    def generate():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            while True:
                try:
                    if state.current_browser_info and 'cdp_endpoint' in state.current_browser_info:
                        screenshot_data = loop.run_until_complete(
                            get_screenshot_via_cdp(state.current_browser_info['cdp_endpoint'])
                        )
                        if screenshot_data:
                            yield f"data: {json.dumps({'type': 'screenshot', 'data': screenshot_data})}\n\n"
                        else:
                            yield ": keep-alive\n\n"
                    else:
                        yield ": keep-alive\n\n"
                    time.sleep(0.5)
                except GeneratorExit:
                    break
                except Exception:
                    yield ": keep-alive\n\n"
                    time.sleep(1)
        finally:
            loop.close()
    return Response(stream_with_context(generate()), mimetype='text/event-stream')
