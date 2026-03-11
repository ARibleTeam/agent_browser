"""Запуск агента в отдельном процессе и перехват логов."""
import asyncio
import logging
import multiprocessing
import re

import app.state as state


def stop_current_agent_process() -> None:
    """Гарантированно остановить текущий процесс агента."""
    if state.current_agent_process and state.current_agent_process.is_alive():
        try:
            state.current_agent_process.terminate()
            state.current_agent_process.join(timeout=2)
            if state.current_agent_process.is_alive():
                state.current_agent_process.kill()
                state.current_agent_process.join()
        except Exception:
            pass
        finally:
            state.current_agent_process = None


def run_agent_process(log_queue, model_name, config, task):
    """Запустить агента в отдельном процессе."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    log_handler = LogHandler(log_queue)
    log_handler.setFormatter(logging.Formatter('%(message)s'))

    loggers_to_capture = [
        'browser_use',
        'browser_use.agent',
        'browser_use.agent.service',
        'browser_use.tools',
        'browser_use.tools.service',
        'cdp_use',
        'cdp_use.client',
    ]
    captured_loggers = []
    for logger_name in loggers_to_capture:
        logger_instance = logging.getLogger(logger_name)
        logger_instance.addHandler(log_handler)
        logger_instance.setLevel(logging.INFO)
        captured_loggers.append(logger_instance)

    async def run_agent():
        from browser_use import Agent, Browser, BrowserProfile
        from app.utils.models import create_model_instance, format_error_message

        model_instance = create_model_instance(model_name, config)
        browser = None
        browser_just_created = False

        try:
            # Флаги для стабильной работы в Docker
            browser_args = [
                '--no-sandbox',  # Требуется для Docker
                '--disable-dev-shm-usage',  # Использовать /tmp вместо /dev/shm
                '--disable-gpu',  # Отключить GPU в headless режиме
                '--disable-software-rasterizer',  # Отключить софтверный растеризатор
            ]
            profile = BrowserProfile(
                headless=False,
                keep_alive=False,
                args=browser_args,
                chromium_sandbox=False
            )
            browser = Browser(browser_profile=profile)
            try:
                # Таймаут 60 секунд для запуска браузера в Docker
                await asyncio.wait_for(browser.start(), timeout=60.0)
                browser_just_created = True
            except Exception as browser_error:
                error_msg = format_error_message(browser_error)
                log_queue.put({
                    'type': 'result',
                    'success': False,
                    'error': f'Ошибка запуска браузера: {error_msg}'
                })
                return None

            agent = Agent(task=task, llm=model_instance, browser=browser)
            try:
                history = await agent.run()
                return history
            except asyncio.CancelledError:
                log_queue.put({
                    'type': 'result',
                    'success': False,
                    'error': 'Выполнение отменено пользователем'
                })
                return None
            except Exception as e:
                from app.utils.models import format_error_message
                log_queue.put({
                    'type': 'result',
                    'success': False,
                    'error': format_error_message(e) or str(e)
                })
                return None
        except Exception:
            if browser_just_created and browser:
                try:
                    await browser.stop()
                except Exception:
                    pass
            return None

    try:
        history = loop.run_until_complete(run_agent())
        if history is not None:
            response_text = "Задача выполнена"
            if history and len(history) > 0:
                last_action = history[-1]
                if hasattr(last_action, 'result') and last_action.result:
                    response_text = str(last_action.result)
            log_queue.put({
                'type': 'result',
                'success': True,
                'response': response_text,
                'history_length': len(history) if history else 0
            })
    except Exception:
        pass
    finally:
        try:
            pending = asyncio.all_tasks(loop)
            for t in pending:
                t.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()
        except Exception:
            pass
        try:
            for logger_instance in captured_loggers:
                logger_instance.removeHandler(log_handler)
        except Exception:
            pass


# Паттерны логов browser_use и как мы их показываем пользователю.
# Порядок важен: более специфичные правила первыми.
# Каждое правило: (маркер в сообщении, тип для фронта, функция форматирования).
# Форматтер возвращает (text, is_final_result=False) или None (не показывать).

def _fmt_step(msg: str):
    m = re.search(r'📍 Step (\d+)(?:\s*:\s*(.+))?', msg, re.DOTALL)
    if m:
        tail = f": {m.group(2).strip()}" if m.group(2) and m.group(2).strip() else ""
        return (f"📍 Шаг {m.group(1)}{tail}", False)
    if '📍 Step' in msg:
        return ("📍 Шаг", False)
    return None


def _fmt_eval(msg: str):
    m = re.search(r'([👍❔]) Eval:\s*(.+)', msg, re.DOTALL)
    if m:
        return (f"{m.group(1)} Оценка: {m.group(2).strip()}", False)
    return None


def _fmt_memory(msg: str):
    m = re.search(r'🧠 Memory:\s*(.+)', msg, re.DOTALL)
    if m:
        return (f"🧠 Память: {m.group(1).strip()}", False)
    return None


def _fmt_goal(msg: str):
    for pattern, prefix in [
        (r'🎯 Next goal:\s*(.+)', '🎯 Следующая цель: '),
        (r'🎯 Task:\s*(.+)', '🎯 Задача: '),
    ]:
        m = re.search(pattern, msg, re.DOTALL)
        if m:
            return (prefix + m.group(1).strip(), False)
    return None


def _fmt_judge(msg: str):
    """
    Логи с вердиктом судьи. Если есть явный PASS/FAIL — считаем это финалом задачи.

    Возвращаем (text, is_final_result), где is_final_result=True означает,
    что по этому сообщению можно завершать задачу на уровне UI.
    """
    if '⚖️' not in msg and 'Judge Verdict' not in msg:
        return None

    text = msg.strip()
    # Считаем, что финальный вердикт всегда содержит PASS или FAIL
    is_final = ('FAIL' in text) or ('PASS' in text)
    return (text, is_final)


def _fmt_final_result(msg: str):
    if '📄' not in msg or 'Final Result' not in msg:
        return None
    m = re.search(r'📄\s*Final Result:\s*(.+)', msg, re.DOTALL)
    if m:
        body = '\n'.join(l.strip() for l in m.group(1).strip().split('\n') if l.strip())
        return (f"📄 Итог:\n{body}", False)
    m = re.search(r'📄\s*(.+)', msg, re.DOTALL)
    if m:
        return (f"📄 {m.group(1).strip()}", False)
    return ("📄 Итог", False)


def _fmt_action(msg: str):
    if '▶️' not in msg:
        return None
    m = re.search(r'▶️\s+(.+)', msg, re.DOTALL)
    return (f"▶️ {m.group(1).strip()}" if m else f"▶️ {msg.strip()}", False)


def _fmt_tool(msg: str):
    # Клик, навигация, ввод, скролл и т.д.
    m = re.search(r'([🖱️🔗⌨️📝🔍])\s*(.+)', msg)
    if m:
        return (f"{m.group(1)} {m.group(2).strip()}", False)
    return None


def _fmt_error(msg: str):
    if '❌' not in msg:
        return None
    m = re.search(r'❌\s*(.+)', msg, re.DOTALL)
    return (f"❌ {m.group(1).strip()}" if m else "❌ Ошибка", False)


def _fmt_result_ok(msg: str):
    if '✅' not in msg:
        return None
    m = re.search(r'✅\s*(.+)', msg, re.DOTALL)
    # Это просто статус‑лог (например, про расширения браузера), а не финальный результат агента.
    # Финальное завершение задачи определяется только самим runner'ом через history/исключения,
    # поэтому здесь никогда не помечаем сообщение как "финальный результат".
    return (f"✅ {m.group(1).strip()}" if m else "✅", False)


# Правила в порядке приоритета: что проверять первым.
_LOG_RULES = [
    ('📍 Step', 'step', _fmt_step),
    ('👍 Eval:', 'eval', _fmt_eval),
    ('❔ Eval:', 'eval', _fmt_eval),
    ('🧠 Memory:', 'memory', _fmt_memory),
    ('🎯 Next goal:', 'goal', _fmt_goal),
    ('🎯 Task:', 'goal', _fmt_goal),
    ('Judge Verdict', 'judge', _fmt_judge),
    ('⚖️', 'judge', _fmt_judge),
    ('Final Result:', 'log', _fmt_final_result),
    ('📄', 'log', _fmt_final_result),
    ('▶️', 'action', _fmt_action),
    ('🖱️', 'tool', _fmt_tool),
    ('🔗', 'tool', _fmt_tool),
    ('⌨️', 'tool', _fmt_tool),
    ('📝', 'tool', _fmt_tool),
    ('🔍', 'tool', _fmt_tool),
    ('❌', 'error', _fmt_error),
    ('✅', 'log', _fmt_result_ok),
]


class LogHandler(logging.Handler):
    """
    Перехватывает логи агента (browser_use, tools, cdp_use) и отправляет в очередь для UI.

    Политика:
    - Показываем все осмысленные события: шаги, оценки, цели, действия, вызовы инструментов,
      ошибки и финальный результат.
    - Сообщение сначала очищается от ANSI-кодов и префиксов логгера.
    - Если строка совпадает с известным форматом — классифицируем и форматируем явно.
    - Если не совпала ни с одним правилом — отправляем как тип 'log', чтобы пользователь
      видел, что происходит, а не «тишину».
    """

    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
        self._ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        self._logger_prefix = re.compile(r'^[A-Z]+\s+\[[^\]]+\]\s+')

    def _clean(self, msg: str) -> str:
        if not msg or not msg.strip():
            return ""
        msg = self._ansi_escape.sub('', msg)
        msg = self._logger_prefix.sub('', msg)
        return msg.strip()

    def emit(self, record):
        try:
            name = record.name
            if not any(x in name for x in ('browser_use', 'Agent', 'tools', 'cdp_use')):
                return
            msg = self._clean(self.format(record))
            if not msg:
                return

            log_type = None
            formatted_msg = None
            is_final_result = False

            for marker, typ, formatter in _LOG_RULES:
                if marker not in msg:
                    continue
                out = formatter(msg)
                if out is None:
                    continue
                formatted_msg, is_final_result = out
                log_type = typ
                break

            # Не отбрасываем непойманные сообщения — показываем как общий лог
            if log_type is None:
                log_type = 'log'
                formatted_msg = msg

            queue_data = {
                'type': log_type,
                'level': record.levelname,
                'message': formatted_msg,
                'logger': name,
            }
            if log_type == 'result' and is_final_result:
                queue_data['success'] = True
                queue_data['response'] = formatted_msg

            # Всегда отправляем основное сообщение (step/goal/judge/…)
            self.log_queue.put(queue_data)

            # Дополнительно: если это вердикт судьи и он финальный — шлём отдельное
            # событие типа `result`, чтобы фронт гарантированно завершил задачу.
            if log_type == 'judge' and is_final_result:
                is_pass = ('PASS' in msg) and ('FAIL' not in msg)
                result_payload = {
                    'type': 'result',
                    'success': is_pass,
                }
                if is_pass:
                    # Условный успех — используем текст вердикта как итоговый ответ
                    result_payload['response'] = formatted_msg
                else:
                    # FAIL — считаем это ошибкой/несоответствием требованиям
                    result_payload['error'] = formatted_msg
                self.log_queue.put(result_payload)
        except Exception:
            pass
