"""Learning settings: <vault>/.mnema/learn.json. Everything has a sane default, the owner can change any of it."""

from __future__ import annotations

from copy import deepcopy

from ..vault import Vault
from . import secrets_store
from ..fsutil import read_json, write_json

SECRET_FIELDS = [("brain", "api_key"), ("mail", "password")]


def _vid(vault: Vault) -> str:
    from . import secrets_store as _ss

    return _ss.vault_id(vault)


MODES = ["off", "observe", "approve", "mixed", "quiet"]
MODES_RU = {
    "off": "выключено",
    "observe": "только наблюдать",
    "approve": "только с одобрения",
    "mixed": "смешанный",
    "quiet": "тихо, всё сама",
}

SOURCES = {
    "mnema_chat": {
        "name": "Разговоры в Mnemai",
        "group": "Разговоры с ИИ",
        "options": {},
        "note": "Твои сообщения и ответы ИИ прямо здесь, в чате. Учится сразу, пока ты пишешь.",
    },
    "claude_code": {
        "name": "Разговоры в Claude Code",
        "group": "Разговоры с ИИ",
        "options": {"path": "~/.claude/projects"},
    },
    "chatgpt_export": {
        "name": "Выгрузка ChatGPT (conversations.json)",
        "group": "Разговоры с ИИ",
        "options": {"path": ""},
    },
    "corrections": {
        "name": "Твои поправки в разговорах с ИИ",
        "group": "Поправки",
        "options": {},
        "note": "Берутся из разговоров с ИИ: \"нет, не так\", \"я же говорил\", \"никогда не…\"",
    },
    "notes": {"name": "Папка заметок", "group": "Заметки", "options": {"path": "", "exclude": ".obsidian,.trash,.git"}},
    "mail": {
        "name": "Почта (отправленные письма)",
        "group": "Почта и Telegram",
        "options": {"host": "", "user": "", "password": "", "folder": "", "days": 30},
    },
    "telegram_api": {
        "name": "Telegram (переписка через API)",
        "group": "Почта и Telegram",
        "options": {},
        "note": "Переписка в чатах, которые ты выбрал: твои сообщения и собеседников. Только чтение. Вход и чаты — Настройки → Обучение → Telegram.",
    },
    "telegram": {
        "name": "Telegram (выгрузка из Telegram Desktop)",
        "group": "Почта и Telegram",
        "options": {"path": ""},
    },
    "calendar": {
        "name": "Календарь",
        "group": "Цифровая жизнь",
        "options": {"path": ""},
        "note": "Файл .ics или секретная ссылка iCal (Google Календарь → настройки).",
    },
    "documents": {
        "name": "Документы",
        "group": "Цифровая жизнь",
        "options": {"path": ""},
        "note": "Папка с документами Word, текстами и заметками. Читаю только новые и изменённые.",
    },
    "browser_history": {
        "name": "История браузера",
        "group": "Цифровая жизнь",
        "options": {"browser": ""},
        "note": "Заголовки прочитанных страниц, по дням. Chrome, Edge или Яндекс.",
    },
}
DEFAULT_ON = {"mnema_chat"}
DEFAULT_MODE = {"browser_history": "observe"}

BRAINS = {
    "auto": "Сама: модель, с которой ты говоришь, иначе только явное",
    "model": "Модель, с которой ты говоришь по умолчанию — любая подключённая",
    "none": "Без модели — только явные сигналы: \"запомни\", поправки, даты статусов",
    "claude_code": "Claude Code, который уже стоит на компьютере",
    "api": "Свой ключ API (Anthropic или совместимый с OpenAI)",
    "ollama": "Локальная модель Ollama — ничего не уходит с компьютера",
    "local": "Встроенная модель Mnemai — ничего не уходит с компьютера",
}

DEFAULT = {
    "sources": {
        sid: {"enabled": sid in DEFAULT_ON, "mode": DEFAULT_MODE.get(sid, "mixed"), "options": deepcopy(s["options"])}
        for sid, s in SOURCES.items()
    },
    # "auto" by default: a client expects learning to work out of the box. "chosen" — the owner picked the kind
    # himself; then it is never changed for him.
    "brain": {"kind": "auto", "model": "", "endpoint": "", "api_key": "", "provider": "anthropic", "chosen": False},
    "auto_confidence": 0.8,  # mixed mode: write silently at or above this
    "ask_cooldown_minutes": 60,  # one question about memory per conversation in this many minutes, not one per fact
    "sensitive_tags": ["money", "health", "private"],
    "never": [],  # "don't learn things like this": phrases and topics
    "forget_after_days": 60,  # learned once, never repeated, never confirmed → offer to forget
    "interval_minutes": 15,
    "max_episodes_per_run": 200,
    "initial": {"done": False, "days": 90},
    # May Mnemai look outside its own chat and memory folder (other programs, the browser, the web)? None — not asked
    # yet, False — "только Mnemai" (nothing else is read, whatever is switched on), True — what is ticked.
    "outside": None,
    "found": {},  # found on this computer, off until the owner ticks it (learn/detect.py)
    "found_asked": True,  # false: the first launch still has to show the list
    "paused": False,
    "demo": False,  # demo memory: never reads the computer
}


def _merge(base: dict, over: dict) -> dict:
    out = deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


LOCAL_ONLY = ("mnema_chat", "corrections")  # learn inside Mnemai itself, never outside it


def allowed(s: dict, sid: str) -> bool:
    """A source really runs: switched on, and inside Mnemai or the owner didn't say "только Mnemai". Before the question
    nothing outside is on anyway: only the owner's own tick switches a source on."""
    src = s["sources"].get(sid) or {}
    return bool(
        src.get("enabled") and src.get("mode") != "off" and (sid in LOCAL_ONLY or s.get("outside") is not False)
    )


def _slot(s: dict, where: str) -> dict:
    return s["brain"] if where == "brain" else s["sources"][where]["options"]


def load(vault: Vault) -> dict:
    f = vault.service / "learn.json"
    data = read_json(f, {}) or {}
    s = _merge(DEFAULT, data)
    _drop_gone(s)
    if (
        "chosen" not in data.get("brain", {"chosen": 1}) and s["brain"].get("kind") == "none"
    ):  # versions before 0.5 wrote "none" by default
        s["brain"]["kind"] = "auto"
    if "outside" not in data and data.get("autodetect"):  # a memory from before the question: what it reads says yes
        s["outside"] = True if any(x.get("enabled") for k, x in s["sources"].items() if k not in LOCAL_ONLY) else None
    if not data.get("autodetect") and not s.get("demo"):  # once per memory: switch on what this computer has
        from . import detect

        if not detect.blocked():
            detect.apply(s)
            save(vault, s)
            if s["found"]:
                try:
                    from .engine import emit

                    emit(
                        vault,
                        "заметила",
                        "нашла, откуда можно учиться, но ничего не читаю, пока не отметишь: "
                        + ", ".join(SOURCES[k]["name"] for k in s["found"]),
                        source="mnema_chat",
                    )
                except Exception:
                    pass
    for where, key in SECRET_FIELDS:  # secrets come from outside the vault
        _slot(s, where)[key] = secrets_store.get(_vid(vault), f"{where}.{key}")
    return s


def _drop_gone(s: dict) -> None:
    """Sources that no longer exist (the web search «Мир вокруг», removed 21.10.2026; the browser extension for ChatGPT
    and Gemini, removed 24.10.2026) leave old settings."""
    s["sources"] = {k: v for k, v in s["sources"].items() if k in SOURCES}
    s["found"] = {k: v for k, v in (s.get("found") or {}).items() if k in SOURCES}


def save(vault: Vault, settings: dict) -> dict:
    s = _merge(DEFAULT, settings)
    _drop_gone(s)
    for sid, src in s["sources"].items():
        if src.get("mode") not in MODES:
            src["mode"] = "mixed"
    on_disk = deepcopy(s)
    for where, key in SECRET_FIELDS:  # never write secrets into the vault
        secrets_store.put(_vid(vault), f"{where}.{key}", _slot(s, where).get(key, ""))
        _slot(on_disk, where)[key] = ""
    vault.service.mkdir(parents=True, exist_ok=True)
    write_json(vault.service / "learn.json", on_disk, indent=2)
    return s


def public(settings: dict) -> dict:
    """Settings for the UI: secrets masked."""
    s = deepcopy(settings)
    if s["brain"].get("api_key"):
        s["brain"]["api_key"] = "••••" + s["brain"]["api_key"][-4:]
    pw = s["sources"]["mail"]["options"].get("password")
    if pw:
        s["sources"]["mail"]["options"]["password"] = "••••"
    return s


def merge_from_ui(current: dict, incoming: dict) -> dict:
    """Masked secrets coming back from the UI keep their stored value."""
    new = _merge(current, incoming)
    if incoming.get("brain", {}).get("kind"):
        new["brain"]["chosen"] = incoming["brain"]["kind"] != "auto"
    if str(incoming.get("brain", {}).get("api_key", "")).startswith("••••"):
        new["brain"]["api_key"] = current["brain"].get("api_key", "")
    inc_pw = incoming.get("sources", {}).get("mail", {}).get("options", {}).get("password", "")
    if str(inc_pw).startswith("••••"):
        new["sources"]["mail"]["options"]["password"] = current["sources"]["mail"]["options"].get("password", "")
    return new


def resolve_brain(s: dict) -> str:
    """The kind that actually works now. "auto": the model the owner talks to (any connected one, none preferred by
    name); without any — explicit signals only."""
    kind = s["brain"].get("kind", "auto")
    if kind != "auto":
        return kind
    import os
    import sys

    if os.environ.get("MNEMA_BRAIN_AUTO"):  # tests and checks pin what "auto" finds
        return os.environ["MNEMA_BRAIN_AUTO"]
    if "unittest" in sys.modules and not getattr(sys, "frozen", False):
        return "none"  # a test run never talks to a live model by accident
    return "model"
