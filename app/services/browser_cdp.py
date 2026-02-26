"""Работа с браузером через Chrome DevTools Protocol: скриншоты и закрытие."""
import asyncio
import json

import requests
import websockets

from app import state


def close_browser_via_cdp() -> None:
    """Закрыть браузер через CDP Browser.close, чтобы не оставлять зомби-процессы."""
    if not state.current_browser_info or 'cdp_endpoint' not in state.current_browser_info:
        return
    try:
        cdp_base = state.current_browser_info['cdp_endpoint']
        resp = requests.get(f'{cdp_base}/json/version', timeout=2)
        if resp.status_code != 200:
            return
        ws_url = resp.json().get('webSocketDebuggerUrl')
        if not ws_url:
            return
        loop = asyncio.new_event_loop()
        async def _close():
            async with websockets.connect(ws_url, close_timeout=2) as ws:
                await ws.send(json.dumps({"id": 1, "method": "Browser.close"}))
                try:
                    await asyncio.wait_for(ws.recv(), timeout=2)
                except Exception:
                    pass
        loop.run_until_complete(_close())
        loop.close()
    except Exception:
        pass


async def get_screenshot_via_cdp(cdp_base_url: str) -> str | None:
    """
    Получить скриншот через CDP.
    cdp_base_url — HTTP-адрес вида http://127.0.0.1:PORT.
    """
    try:
        resp = requests.get(f'{cdp_base_url}/json', timeout=2)
        if resp.status_code != 200:
            return None
        targets = resp.json()
        page_ws_url = None
        for target in targets:
            if target.get('type') == 'page':
                page_ws_url = target.get('webSocketDebuggerUrl')
                if page_ws_url:
                    break
        if not page_ws_url:
            return None
        async with websockets.connect(page_ws_url, close_timeout=2) as ws:
            await ws.send(json.dumps({
                "id": 1,
                "method": "Page.captureScreenshot",
                "params": {"format": "png"}
            }))
            raw = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(raw)
            if "result" in data and "data" in data["result"]:
                return data["result"]["data"]
        return None
    except Exception:
        return None
