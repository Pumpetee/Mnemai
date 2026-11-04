"""Errors in the owner's words: what happened and what to do — never a raw exception, an HTTP code or English.

human(e, who) is used wherever a request to an AI, a search, a download or a VPN can fail: the chat, the consortium,
the list of models, the meeting scribe. `who` is the service as the owner knows it ("ChatGPT", "Claude").
"""

from __future__ import annotations

import json
import re
import socket
import ssl
import urllib.error

KEYS = "Настройки → ИИ и модели"
NET = "Настройки → VPN и прокси"


class Cut(RuntimeError):
    """The answer stopped in the middle: the connection dropped or the service broke off."""


def _body(e: urllib.error.HTTPError) -> str:
    try:
        raw = e.read() if hasattr(e, "read") else b""
        e.body_text = getattr(e, "body_text", None) or raw.decode("utf-8", "replace")
    except Exception:
        e.body_text = getattr(e, "body_text", "") or ""
    return e.body_text


def _provider_message(body: str) -> str:
    try:
        d = json.loads(body)
    except ValueError:
        return ""
    if isinstance(d, list) and d:
        d = d[0]
    err = d.get("error") if isinstance(d, dict) else None
    if isinstance(err, dict):
        return str(err.get("message") or err.get("type") or "")
    return str(err or (d.get("message") if isinstance(d, dict) else "") or "")


def bad_key(code: int, msg: str) -> bool:
    """Gemini answers a wrong key with 400 «API key not valid», not 401."""
    return (
        code == 400
        and bool(re.search(r"api.?key|api_key_invalid", msg))
        and bool(re.search(r"invalid|not valid|valid api key|expired", msg))
    )


def http(code: int, body: str, who: str, model: str = "") -> str:
    msg = _provider_message(body).lower()
    quota = any(w in msg for w in ("quota", "billing", "credit", "insufficient", "balance", "payment"))
    if code in (401, 403) and not quota or bad_key(code, msg):
        return f"{who} не принял ключ: проверь, что он скопирован целиком и не отозван, или создай новый — {KEYS}."
    if code == 402 or quota:
        return (
            f"{who}: на счёте кончились деньги или лимит. Пополни баланс у {who} или выбери другую модель слева вверху."
        )
    if code == 429:
        return f"{who} просит подождать: слишком много запросов подряд. Повтори через минуту."
    if code in (400, 404) and re.search(
        r"deprecated|not a chat model|not supported in the v1/chat/completions|only supported in v1/responses|"
        r"modality contain audio|no longer available",
        msg,
    ):
        what = f"Модель «{model}»" if model else "Эта модель"
        return (
            f"{what} у {who} больше не работает в чате (снята с поддержки или сделана не для разговора) — "
            "я убрала её из списка. Выбери другую слева вверху."
        )
    if code == 404:
        what = f"«{model}»" if model else "эта модель"
        return f"У {who} нет модели {what}: выбери другую слева вверху или обнови список — {KEYS}."
    if code == 413 or "too long" in msg or "context length" in msg or "maximum context" in msg:
        return "Запрос слишком длинный для этой модели: начни новый разговор или прикрепи документ поменьше."
    if code == 400:
        return f"{who} отклонил запрос. Попробуй другую модель слева вверху." + (
            f" Ответ сервиса: {msg[:160]}" if msg else ""
        )
    if code >= 500 or "overloaded" in msg:
        return f"{who} сейчас перегружен или сбоит. Повтори через минуту или выбери другую модель слева вверху."
    return f"{who} ответил ошибкой {code}. Повтори позже или выбери другую модель слева вверху."


def human(e: BaseException, who: str = "сервис", model: str = "", vpn: str = "") -> str:
    """vpn — the name of the VPN key Mnemai connects through, if any: then the tunnel is the first suspect."""
    via = (
        f"Связь идёт через VPN «{vpn}» — похоже, его сервер не отвечает: проверь ключ или выключи его — {NET}."
        if vpn
        else ""
    )
    if isinstance(e, urllib.error.HTTPError):
        return http(e.code, _body(e), who, model)
    if isinstance(e, Cut):
        return f"Ответ {who} оборвался на середине: связь прервалась. Нажми «Ещё раз»." + (f" {via}" if via else "")
    reason = getattr(e, "reason", e) if isinstance(e, urllib.error.URLError) else e
    text = str(reason)
    if isinstance(reason, (socket.timeout, TimeoutError)) or "timed out" in text:
        return via or f"{who} не ответил вовремя. Проверь интернет или прокси и повтори — {NET}."
    if isinstance(reason, ssl.SSLError) or "EOF occurred" in text or "UNEXPECTED_EOF" in text:
        return (
            via
            or f"Связь с {who} обрывается: такое бывает из-за прокси, VPN или антивируса. Проверь подключение — {NET}."
        )
    if isinstance(reason, socket.gaierror) or "getaddrinfo" in text or "11001" in text:
        return via or f"Нет связи с {who}: похоже, нет интернета. Проверь подключение или прокси — {NET}."
    if isinstance(reason, ConnectionRefusedError) or "10061" in text:
        return via or f"Нет связи с {who}: прокси или сеть не отвечает. Проверь интернет и настройки прокси — {NET}."
    if isinstance(reason, (ConnectionResetError, ConnectionAbortedError)) or re.search(
        r"1005[34]|RemoteDisconnected", text
    ):
        return via or f"Связь с {who} прервалась. Повтори — если не поможет, проверь интернет или прокси — {NET}."
    if re.search(r"[А-Яа-яЁё]", text) and not re.search(r"\[WinError|Errno|codec", text):
        return text[:400]  # Mnemai's own message, already for the owner
    if isinstance(e, MemoryError):
        return "Не хватило оперативной памяти: закрой лишние программы и повтори."
    return f"Не получилось получить ответ от {who}. Повтори; если не поможет — выбери другую модель слева вверху."


def no_network(e: BaseException) -> bool:
    """The internet itself is missing: no address resolves, nothing connects, nothing answers in time."""
    if isinstance(e, urllib.error.HTTPError):
        return False
    reason = getattr(e, "reason", e) if isinstance(e, urllib.error.URLError) else e
    text = str(reason)
    return isinstance(reason, (socket.gaierror, socket.timeout, TimeoutError, ConnectionRefusedError)) or bool(
        re.search(r"getaddrinfo|11001|10051|10065|10060|timed out|Network is unreachable", text)
    )


def account_problem(e: BaseException) -> bool:
    """The key, the money or the program itself: asking again in the next round will not help."""
    from .chat.providers import AccountProblem, NotSent

    if isinstance(e, (NotSent, AccountProblem)):
        return True
    if isinstance(e, urllib.error.HTTPError):
        if e.code in (401, 402, 403) or bad_key(e.code, _provider_message(_body(e)).lower()):
            return True
        if e.code == 429:
            msg = _provider_message(_body(e)).lower()
            return any(w in msg for w in ("quota", "billing", "credit", "insufficient", "balance"))
    return False


def provider_name(pid: str) -> str:
    return {
        "claude_code": "Claude",
        "codex": "ChatGPT по подписке",
        "opencode_go": "OpenCode Go",
        "anthropic": "Claude",
        "openai": "ChatGPT",
        "gemini": "Gemini",
        "openrouter": "OpenRouter",
        "deepseek": "DeepSeek",
        "yandex": "YandexGPT",
        "ollama": "Ollama",
        "strata": "Strata",
        "local": "Модель на компьютере",
    }.get(pid, pid or "сервис")


def vpn_name(vault) -> str:
    try:
        from .agent import profile as P

        p = P.load(vault)
        return str(p.get("vpn_name") or "VPN") if p.get("vpn_key_on") else ""
    except Exception:
        return ""
