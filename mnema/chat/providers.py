"""Models for the chat: Claude by subscription (the installed Claude Code), own keys (Anthropic, OpenAI, Gemini,
OpenRouter) and a local Ollama. Every provider streams text pieces.

Keys live in the Windows-protected secrets store, never in the memory folder. Model lists are fetched from the
provider itself — nothing is guessed.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path
from typing import Iterator

import datetime as dt

from .. import net
from .. import tuning as _tuning
from ..learn import secrets_store
from ..learn.brains import claude_exe, claude_settings_env, claude_signed_in
from ..vault import Vault
from ..fsutil import read_json, write_json
from . import model_rank

PROVIDERS = {
    "local": {
        "name": "Встроенная модель",
        "note": "Работает на этом компьютере, без интернета и ключей.",
        "client": "local",
        "key": False,
    },
    "claude_code": {
        "name": "Claude по подписке",
        "note": "Через установленный Claude Code. Ключ не нужен.",
        "client": "claude",
        "key": False,
        "subscription": True,
    },
    "codex": {
        "name": "ChatGPT по подписке",
        "note": "Официальный вход ChatGPT; запросы считаются по лимиту подписки.",
        "client": "chatgpt",
        "key": False,
        "subscription": True,
    },
    "anthropic": {
        "name": "Claude · ключ API",
        "note": "Ключ API от Anthropic.",
        "client": "claude",
        "key": True,
        "base": "https://api.anthropic.com",
    },
    "openai": {
        "name": "ChatGPT",
        "note": "Ключ API от OpenAI.",
        "client": "chatgpt",
        "key": True,
        "base": "https://api.openai.com/v1",
    },
    "opencode_go": {
        "name": "OpenCode Go",
        "note": "Ключ подписки OpenCode Go. Хранится в защищённом хранилище системы.",
        "client": "opencode",
        "key": True,
        "subscription": True,
        "base": "https://opencode.ai/inference/go/openai/v1",
    },
    "gemini": {
        "name": "Gemini",
        "note": "Свой ключ Google AI Studio.",
        "client": "gemini",
        "key": True,
        "base": "https://generativelanguage.googleapis.com/v1beta/openai",
    },
    "openrouter": {
        "name": "OpenRouter",
        "note": "Один ключ — сотни моделей.",
        "client": "openrouter",
        "key": True,
        "base": "https://openrouter.ai/api/v1",
    },
    "deepseek": {
        "name": "DeepSeek",
        "note": "Ключ API от DeepSeek.",
        "client": "deepseek",
        "key": True,
        "base": "https://api.deepseek.com",
    },
    "yandex": {
        "name": "YandexGPT",
        "note": "Ключ API и ID каталога Yandex Cloud AI Studio.",
        "client": "yandex",
        "key": True,
        "base": "https://ai.api.cloud.yandex.net/v1",
    },
    "ollama": {
        "name": "Ollama",
        "note": "Всё остаётся на компьютере.",
        "client": "local",
        "key": False,
        "base": "http://127.0.0.1:11434",
    },
    "strata": {
        "name": "Strata",
        "note": "Большие модели на этом компьютере: Qwen, DeepSeek. Без ключа и интернета.",
        "client": "local",
        "key": False,
        "base": "http://127.0.0.1:8080/v1",
    },
}
# Yandex Cloud AI Studio has no list of models over its OpenAI-compatible API: the text models of its catalogue
# (aistudio.yandex.ru/docs/en/ai-studio/concepts/generation/models), addressed as gpt://<folder>/<id>
YANDEX_MODELS = [
    "aliceai-llm",
    "yandexgpt-5.1",
    "yandexgpt-5-pro",
    "aliceai-llm-flash",
    "deepseek-v4.1-flash",
    "qwen3.6-35b-a3b",
]
CLAUDE_CODE_MODELS = [("", "Claude"), ("sonnet", "Claude Sonnet"), ("opus", "Claude Opus"), ("haiku", "Claude Haiku")]


def _vid(vault: Vault) -> str:
    return secrets_store.vault_id(vault)


def _cfg_file(vault: Vault) -> Path:
    return vault.service / "providers.json"


def load(vault: Vault) -> dict:
    f = _cfg_file(vault)
    data = read_json(f, {}) or {}
    for pid in PROVIDERS:
        data.setdefault(pid, {"models": [], "endpoint": ""})
    return data


def save(
    vault: Vault,
    pid: str,
    models: list | None = None,
    endpoint: str | None = None,
    key: str | None = None,
    disabled: bool | None = None,
    created: dict | None = None,
    folder: str | None = None,
) -> dict:
    """disabled: the owner switched this AI off — it leaves every list of models, its key and models stay."""
    if pid not in PROVIDERS:
        raise ValueError("нет такого провайдера")
    data = load(vault)
    if disabled is not None:
        data[pid]["disabled"] = bool(disabled)
        data[pid].pop("problem", None)  # switched back on — tried afresh
    if models is not None:
        data[pid]["models"] = [m for m in models if isinstance(m, str) and m.strip()][:400]
    if created is not None:
        data[pid]["created"] = created
    if endpoint is not None:
        data[pid]["endpoint"] = endpoint.strip()
    if folder is not None:  # YandexGPT: the Yandex Cloud folder the key belongs to
        data[pid]["folder"] = folder.strip()
    if key is not None and not key.startswith("••••"):
        secrets_store.put(_vid(vault), f"chat.{pid}", key.strip())
    vault.service.mkdir(parents=True, exist_ok=True)
    write_json(_cfg_file(vault), data, indent=2)
    return data


def key_of(vault: Vault, pid: str) -> str:
    return secrets_store.get(_vid(vault), f"chat.{pid}")


def folder_of(vault: Vault, pid: str = "yandex") -> str:
    return (load(vault).get(pid) or {}).get("folder", "")


def base_of(vault: Vault, pid: str) -> str:
    return (load(vault)[pid].get("endpoint") or PROVIDERS[pid].get("base", "")).rstrip("/")


LIMIT_RETRY = 30 * 60  # a reached limit is tried again in half an hour; a refused key or account waits for «Проверить»


def problem_of(data: dict, pid: str) -> str:
    pr = data.get(pid, {}).get("problem") or {}
    if not pr.get("text"):
        return ""
    if pr.get("kind") == "limit" and time.time() - float(pr.get("at") or 0) > LIMIT_RETRY:
        return ""
    return str(pr["text"])


def note_problem(vault: Vault, pid: str, text: str, kind: str = "account") -> None:
    """The AI is connected but does not work: no money, the subscription ended, the key was refused, a limit.
    The tile says so and the AI leaves the lists of models until it is checked again."""
    if pid not in PROVIDERS or pid in ("local", "ollama"):
        return
    data = load(vault)
    data[pid]["problem"] = {"text": text[:400], "kind": kind, "at": time.time()}
    vault.service.mkdir(parents=True, exist_ok=True)
    write_json(_cfg_file(vault), data, indent=2)


def clear_problem(vault: Vault, pid: str) -> None:
    data = load(vault)
    if pid in data and data[pid].pop("problem", None) is not None:
        write_json(_cfg_file(vault), data, indent=2)


def status(vault: Vault) -> list[dict]:
    """ready — the AI can answer now: connected, not switched off, no known problem with the account.
    connected — set up at all (a key, a sign-in, a model), whatever its state."""
    data = load(vault)
    out = []
    for pid, p in PROVIDERS.items():
        key = key_of(vault, pid) if p["key"] else ""
        if pid == "local":
            from .. import localllm

            inst = localllm.installed_models()
            ready, models = bool(inst and localllm.engine_ok()), [{"id": m["id"], "name": m["name"]} for m in inst]
        else:
            ready = (
                claude_signed_in()
                if pid == "claude_code"
                else _codex_signed_in(vault) and _codex_found()
                if pid == "codex"
                else bool(key and data[pid].get("folder"))
                if pid == "yandex"
                else bool(key)
                if p["key"]
                else bool(data[pid]["models"])
            )
            models = (
                [{"id": m, "name": n} for m, n in CLAUDE_CODE_MODELS]
                if pid == "claude_code"
                else [
                    {
                        "id": m,
                        "name": m,
                        **(
                            {"old": True}
                            if model_rank.old(m) and pid not in ("ollama", "strata", "yandex", "codex", "opencode_go")
                            else {}
                        ),
                    }
                    for m in model_rank.rank(pid, data[pid]["models"], data[pid].get("created"))
                ]
            )
        off, problem = bool(data[pid].get("disabled")), problem_of(data, pid) if ready else ""
        out.append(
            {
                "id": pid,
                "name": p["name"],
                "note": p["note"],
                "needs_key": p["key"],
                "subscription": bool(p.get("subscription")),
                "ready": ready and not off and not problem,
                "connected": ready,
                "found": bool(claude_exe()) if pid == "claude_code" else _codex_found() if pid == "codex" else ready,
                "disabled": off,
                "problem": problem,
                "key": ("••••" + key[-4:]) if key else "",
                "endpoint": data[pid].get("endpoint", ""),
                **({"folder": data[pid].get("folder", "")} if pid == "yandex" else {}),
                "models": models,
            }
        )
    return out


def _get(url: str, headers: dict, timeout: int = 20) -> dict:
    with net.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_models(vault: Vault, pid: str) -> list[str]:
    """Ask the provider which models exist — nothing hard-coded."""
    if pid == "claude_code":
        return [m for m, _ in CLAUDE_CODE_MODELS]
    if pid == "codex":
        from . import codex_server as CS

        acc = CS.account(vault)
        if acc.get("type") != "chatgpt":
            raise CS.CodexError(
                "Подписка ChatGPT не подключена. Нажми «Продолжить с ChatGPT» и разреши её использование.",
                "login",
            )
        rows = CS.models(vault)
        ids = [str(m["id"]) for m in rows if m.get("id")]
        if not ids:
            raise CS.CodexError("Codex не вернул доступных моделей для этого аккаунта.", "models")
        save(vault, pid, models=ids, created={})
        clear_problem(vault, pid)
        return ids
    if pid == "local":
        from .. import localllm

        return [m["id"] for m in localllm.installed_models()]
    base, key = base_of(vault, pid), key_of(vault, pid)
    created: dict[str, float] = {}  # the provider's own date of each model: the newest good ones go on top
    if pid == "anthropic":
        d = _get(base + "/v1/models?limit=100", {"x-api-key": key, "anthropic-version": "2023-06-01"})
        ids = [m["id"] for m in d.get("data", [])]
        for m in d.get("data", []):
            try:
                created[m["id"]] = dt.datetime.fromisoformat(
                    str(m.get("created_at")).replace("Z", "+00:00")
                ).timestamp()
            except (ValueError, TypeError):
                pass
    elif pid == "ollama":
        ids = [m["name"] for m in _get(base + "/api/tags", {}).get("models", [])]
    elif pid == "yandex":
        folder = folder_of(vault)
        if not key or not folder:
            raise NotSent("Нужны ключ API и ID каталога Yandex Cloud")
        _yandex_ping(base, key, folder)  # no list to ask for: a one-token request checks the key and the folder
        ids = list(YANDEX_MODELS)
    elif pid == "strata":
        ids = [
            m.get("id", "")
            for m in _get(base + "/models", {"Authorization": f"Bearer {key or 'strata'}"}).get("data", [])
        ]
    elif pid == "opencode_go":
        d = _get(
            "https://opencode.ai/inference/go/v1/models",
            _opencode_headers(key, "mnemai-model-catalog"),
        )
        ids = [m.get("id", "") for m in d.get("data", [])]
    else:
        if pid == "openrouter":  # its list of models is public: the key is checked on its own
            _get(base + "/key", {"Authorization": f"Bearer {key}"})
        d = _get(base + "/models", {"Authorization": f"Bearer {key}"})
        ids = [m.get("id", "").removeprefix("models/") for m in d.get("data", [])]
        created = {
            m.get("id", "").removeprefix("models/"): float(m["created"])
            for m in d.get("data", [])
            if isinstance(m.get("created"), (int, float))
        }
        if pid == "openai":
            ids = [i for i in ids if i.startswith(("gpt", "o1", "o3", "o4", "chatgpt"))] or ids
    ids = sorted({i for i in ids if i and not NOT_CHAT.search(i)}) if pid in PROBE else sorted({i for i in ids if i})
    if pid in PROBE and pid != "yandex":
        ids = usable(vault, pid, ids)  # what the provider lists is not what answers in a chat: each one is asked
    ids = model_rank.rank(pid, ids, created)
    save(vault, pid, models=ids, created={i: created[i] for i in ids if i in created})
    clear_problem(vault, pid)  # the key works again
    return ids


# The providers whose list of models is checked model by model. OpenAI's list holds about a hundred names, and in a
# chat only a third of them answer: the rest are retired (o4-mini, gpt-4, o1…), made for sound, pictures or voice, or
# open only through another API (pro, codex). OpenRouter lists hundreds of chat models and is not asked one by one.
PROBE = {"openai", "gemini", "deepseek", "yandex"}
NOT_CHAT = re.compile(
    r"image|audio|realtime|tts|transcri|embed|moderation|dall-e|whisper|sora|davinci|babbage|imagen|veo|aqa|"
    r"native-audio|live-|computer-use",
    re.I,
)
GONE = re.compile(
    r"deprecated|not a chat model|not supported in the v1/chat/completions|only supported in v1/responses|"
    r"does not exist|model_not_found|not found for API version|is not found|modality contain audio|no longer available",
    re.I,
)


def _probe(vault: Vault, pid: str, mid: str):
    """One tiny request: True — it answers, False — the provider says it is not a chat model or is gone,
    None — can't tell now (a limit, a busy server, no network): the model stays."""
    from .. import errors as E

    base, key = base_of(vault, pid), key_of(vault, pid)
    folder = folder_of(vault) if pid == "yandex" else ""
    body = {
        "model": f"gpt://{folder}/{mid}" if pid == "yandex" else mid,
        "messages": [{"role": "user", "content": "ok"}],
    }
    body["max_completion_tokens" if pid == "openai" else "max_tokens"] = 16
    req = urllib.request.Request(
        base + "/chat/completions",
        method="POST",
        data=json.dumps(body).encode(),
        headers=_yandex_headers(key, folder)
        if pid == "yandex"
        else {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with net.urlopen(req, timeout=40) as r:
            r.read()
        return True
    except urllib.error.HTTPError as e:
        body_text = E._body(e)
        if e.code in (400, 404) and GONE.search(body_text):
            return False
        if e.code == 404:
            return False
        return None
    except Exception:  # noqa: BLE001
        return None


def usable(vault: Vault, pid: str, ids: list[str]) -> list[str]:
    import concurrent.futures as cf

    with cf.ThreadPoolExecutor(8) as ex:
        res = dict(zip(ids, ex.map(lambda m: _probe(vault, pid, m), ids)))
    return [m for m in ids if res.get(m) is not False]


def forget_model(vault: Vault, pid: str, mid: str) -> None:
    """A model the provider has retired or that is not a chat model leaves the saved list at its first refusal."""
    data = load(vault)
    ms = data.get(pid, {}).get("models", [])
    if mid in ms:
        save(vault, pid, models=[m for m in ms if m != mid])


_strata_looked: set[str] = set()


def find_strata(vault: Vault) -> None:
    """Strata, once per start of Mnemai: if it runs on its usual address and isn't connected yet, take its models.
    A quiet, quick look on this computer only; nothing happens if it isn't there."""
    import os

    root = str(vault.root)
    if root in _strata_looked or os.environ.get("MNEMA_NO_DETECT"):
        return
    _strata_looked.add(root)
    if load(vault)["strata"].get("models"):
        return
    try:
        d = _get(base_of(vault, "strata") + "/models", {"Authorization": "Bearer strata"}, timeout=1)
    except Exception:  # noqa: BLE001 — not running, not installed: nothing to say
        return
    ids = [m.get("id", "") for m in d.get("data", []) if m.get("id")]
    if ids:
        save(vault, "strata", models=ids)


def _yandex_ping(base: str, key: str, folder: str) -> None:
    req = urllib.request.Request(
        base + "/chat/completions",
        method="POST",
        data=json.dumps(
            {
                "model": f"gpt://{folder}/aliceai-llm-flash",
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "ok"}],
            }
        ).encode(),
        headers=_yandex_headers(key, folder),
    )
    with net.urlopen(req, timeout=30) as r:
        r.read()


def _yandex_headers(key: str, folder: str) -> dict:
    return {"Authorization": f"Bearer {key}", "OpenAI-Project": folder, "Content-Type": "application/json"}


def _opencode_headers(key: str, session_id: str) -> dict:
    from .. import __version__

    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": f"Mnemai/{__version__}",
        "x-opencode-session": session_id,
    }


def claude_login() -> dict:
    """«Войти»: Claude Code in its own terminal window — it asks for the sign-in on its first start (or type /login)."""
    exe = claude_exe()
    if not exe:
        return {"ok": False, "error": "Claude Code на этом компьютере не найден."}
    try:
        if sys.platform == "win32":
            subprocess.Popen(
                ["cmd.exe", "/c", "start", "Claude Code", exe], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
        elif sys.platform == "darwin":
            subprocess.Popen(
                [
                    "osascript",
                    "-e",
                    f'tell application "Terminal" to do script "{exe}"',
                    "-e",
                    'tell application "Terminal" to activate',
                ]
            )
        else:
            for term in (["x-terminal-emulator", "-e"], ["gnome-terminal", "--"], ["konsole", "-e"], ["xterm", "-e"]):
                if shutil.which(term[0]):
                    subprocess.Popen(term + [exe])
                    break
            else:
                return {"ok": False, "error": f"Открой терминал и запусти: {exe}"}
    except OSError as e:
        return {"ok": False, "error": f"Не открылось окно Claude Code: {e}. Запусти вручную: {exe}"}
    return {"ok": True}


def codex_login(vault: Vault) -> dict:
    from . import codex_server as CS

    return CS.login(vault)


def _codex_found() -> bool:
    from . import codex_server as CS

    return bool(CS.executable())


def _codex_signed_in(vault: Vault) -> bool:
    from . import codex_server as CS

    try:
        return CS.account(vault).get("type") == "chatgpt"
    except Exception:  # noqa: BLE001 — status should still show other providers if Codex is broken
        return False


def check(vault: Vault, pid: str) -> dict:
    """«Проверить снова»: a real, tiny request. Clears a stale problem or records the current one."""
    from .. import errors as E

    clear_problem(vault, pid)
    who = E.provider_name(pid)
    try:
        if pid == "claude_code":
            if not claude_exe():
                return {
                    "ok": False,
                    "error": "Claude Code на этом компьютере не найден. Установи его и нажми «Проверить снова».",
                }
            if not claude_signed_in():
                return {
                    "ok": False,
                    "error": "Claude Code найден, но вход в аккаунт не выполнен: нажми «Войти» и войди своей подпиской Claude.",
                }
            complete(
                vault,
                pid,
                "haiku",
                "",
                [{"role": "user", "text": "Ответь одним словом: да"}],
                meta={"purpose": "проверка подключения"},
            )
        elif pid == "codex":
            models = fetch_models(vault, pid)
            complete(
                vault,
                pid,
                models[0],
                "",
                [{"role": "user", "text": "Ответь одним словом: да"}],
                meta={"purpose": "проверка подключения"},
            )
        else:
            fetch_models(vault, pid)
    except Exception as e:
        msg = E.human(e, who, vpn=E.vpn_name(vault))
        if E.account_problem(e) and not isinstance(e, NotSent):
            note_problem(vault, pid, msg, getattr(e, "kind", "account"))
        return {"ok": False, "error": msg}
    return {"ok": True}


# ---------------------------------------------------------------- streaming


class NotSent(RuntimeError):
    """Nothing left the computer: no program, no key, no model chosen."""


class AccountProblem(RuntimeError):
    """The AI answered, but the account cannot be used: a limit, no money, the subscription ended, signed out.
    kind: limit | money | login."""

    def __init__(self, text: str, kind: str = "money"):
        super().__init__(text)
        self.kind = kind


AFTER = "Пока выбери другую модель слева вверху или выключи Claude по подписке — Настройки → ИИ и модели."


def claude_problem(text: str) -> AccountProblem | RuntimeError:
    """What Claude Code says when it cannot answer — in the owner's words. Its own messages are English and terse:
    «Claude AI usage limit reached|1761400000», «You've hit your limit · resets 5pm», «Credit balance is too low»,
    «Invalid API key · Please run /login», «OAuth token has expired»."""
    t = (text or "").strip()
    low = t.lower()
    if re.search(
        r"usage limit|limit reached|hit your (usage )?limit|out of (extra )?usage|weekly limit|rate.?limit", low
    ):
        when = ""
        m = re.search(r"\|(\d{10})\b", t)
        if m:
            when = " — снова заработает в " + time.strftime("%H:%M", time.localtime(int(m.group(1))))
        else:
            m = re.search(r"resets?\s+(?:at\s+)?([^·|()\n]{1,24})", t, re.I)
            if m:
                when = f" — снова заработает: {m.group(1).strip()}"
        return AccountProblem(f"У подписки Claude кончился лимит{when}. {AFTER}", "limit")
    if re.search(
        r"/login|oauth|token (has )?expired|invalid api key|not (logged|signed) in|please log ?in|"
        r"authenticat|unauthori[sz]ed|\b401\b",
        low,
    ):
        return AccountProblem(
            "Claude Code вышел из аккаунта или вход устарел: открой Claude Code и войди заново (команда /login). "
            + AFTER,
            "login",
        )
    if re.search(
        r"credit balance|billing|subscription|payment|upgrade|no longer|does not have access|"
        r"doesn't have access|not have access|disabled|\b402\b|\b403\b",
        low,
    ):
        return AccountProblem(
            "Подписка Claude не активна или на счёте нет денег. Продли её у Anthropic. " + AFTER, "money"
        )
    if re.search(r"overloaded|\b529\b|\b5\d\d\b|internal server error", low):
        return RuntimeError("Claude сейчас перегружен. Повтори через минуту или выбери другую модель слева вверху.")
    return RuntimeError(
        f"Claude по подписке не ответил: {t[:200] or 'без объяснений'}. Повтори или выбери другую модель."
    )


def _never_connected(e: BaseException) -> bool:
    """The request never reached the service: refused, no such host, no route. Not a timeout after sending."""
    import socket
    import urllib.error

    if isinstance(e, urllib.error.HTTPError):
        return False
    reason = getattr(e, "reason", e) if isinstance(e, urllib.error.URLError) else e
    return isinstance(reason, (ConnectionRefusedError, socket.gaierror)) or (
        isinstance(reason, OSError) and getattr(reason, "winerror", None) in (10061, 10065, 10051, 11001)
    )


def _sse(req: urllib.request.Request, timeout: int = 600, abort: dict | None = None) -> Iterator[dict]:
    """Events of a streamed answer. {"_done": True} comes last when the service said it finished ([DONE])."""
    with net.urlopen(req, timeout=timeout) as r:
        if abort is not None:
            abort["r"] = r
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                yield {"_done": True}
                return
            try:
                yield json.loads(data)
            except ValueError:
                continue


def _flatten(system: str, messages: list[dict]) -> str:
    """Claude Code runs one prompt per call: the conversation goes in as text."""
    hist = []
    for m in messages[:-1]:
        who = "Владелец" if m["role"] == "user" else "Ты"
        hist.append(f"[{who}]\n{m['text']}")
    last = messages[-1]["text"] if messages else ""
    head = "Продолжи разговор. Ниже предыдущие сообщения и новое сообщение владельца.\n\n" if hist else ""
    return head + ("\n\n".join(hist) + "\n\n[Владелец — новое сообщение]\n" if hist else "") + last


def stream(
    vault: Vault,
    pid: str,
    model: str,
    system: str,
    messages: list[dict],
    stop=None,
    usage: dict | None = None,
    meta: dict | None = None,
) -> Iterator[str]:
    """A request to an AI. To a cloud AI secrets are swapped for labels first (Настройки → «Скрывать секреты»), the answer
    gets the real values back on the computer, and the request is written to «Что ушло наружу». meta: purpose, chat,
    memory_sent / memory_full, hidden_tags / hidden_parts, web — for that log."""
    from .. import outgoing as OG
    from .. import tuning

    if pid in tuning.FREE:
        yield from _stream_raw(vault, pid, model, system, messages, stop, usage, meta)
        return
    from ..agent import profile as P

    red = OG.Redactor() if P.load(vault).get("redact", True) else None
    if red:
        system = red.apply(system)
        messages = [{**m, "text": red.apply(m.get("text") or "")} for m in messages]
        if red.values:
            system += "\n\n" + OG.NOTE
    logged = [False]

    def sent():  # written once the request really left: not for a missing program or a refused connection
        if not logged[0]:
            logged[0] = True
            OG.log(
                vault,
                pid,
                model,
                len(system) + sum(len(m.get("text") or "") for m in messages),
                red.summary() if red else {},
                meta,
            )

    if usage is not None and red and red.values:
        usage["redacted"] = red.summary()
    inner = _stream_raw(vault, pid, model, system, messages, stop, usage, meta)
    got = False
    try:
        for piece in red.restore_stream(inner) if red and red.values else inner:
            sent()
            got = True
            yield piece
        sent()
    except NotSent:
        raise
    except GeneratorExit:
        sent()
        raise
    except Exception as e:
        if not _never_connected(e):
            sent()
        _remember_problem(vault, pid, e)
        _drop_if_gone(vault, pid, model, e)
        raise
    if got and problem_of(load(vault), pid):
        clear_problem(vault, pid)


def _drop_if_gone(vault: Vault, pid: str, model: str, e: BaseException) -> None:
    """The provider says this model is retired or not a chat model: it leaves the list, the owner picks another."""
    from .. import errors as E

    try:
        if isinstance(e, urllib.error.HTTPError) and e.code in (400, 404) and GONE.search(E._body(e)):
            forget_model(vault, pid, model)
            e.model_gone = True
    except Exception:  # noqa: BLE001
        pass


def _remember_problem(vault: Vault, pid: str, e: BaseException) -> None:
    from .. import errors as E

    try:
        if E.account_problem(e):
            note_problem(vault, pid, E.human(e, E.provider_name(pid)), getattr(e, "kind", "account"))
    except Exception:
        pass


def _stream_raw(
    vault: Vault,
    pid: str,
    model: str,
    system: str,
    messages: list[dict],
    stop=None,
    usage: dict | None = None,
    meta: dict | None = None,
) -> Iterator[str]:
    """Yield text pieces of the answer. messages: [{role: user|assistant, text}].
    usage (optional) gets filled with tokens spent: {"in", "out", "cache"} as the provider reports them."""
    usage = usage if usage is not None else {}
    if pid == "codex":
        from . import codex_server as CS
        from . import codex_auth as CA

        if not model:
            raise NotSent("Выбери модель Codex")
        try:
            yield from CS.stream(vault, model, system, messages, stop=stop)
        except (CS.CodexError, CA.AuthError) as exc:
            if getattr(exc, "code", "") == "login" or isinstance(exc, CA.AuthError):
                raise AccountProblem(str(exc), "login") from exc
            if getattr(exc, "code", "") == "limit":
                raise AccountProblem(str(exc), "limit") from exc
            raise RuntimeError(str(exc)) from exc
        return
    if pid == "claude_code":
        exe = claude_exe()
        if not exe:
            raise NotSent(
                "Claude по подписке недоступен: на этом компьютере нет Claude Code. Выбери другую модель слева вверху "
                "или подключи ключ — Настройки → ИИ и модели."
            )
        cwd = Path(tempfile.gettempdir()) / "mnema-chat"
        cwd.mkdir(exist_ok=True)
        # the system prompt carries memory and can be long: a file, not the command line (32k limit on Windows)
        fd, sp_path = tempfile.mkstemp(suffix=".txt", dir=cwd)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(system)
        binary = [f for f in (messages[-1].get("files") or []) if f.get("kind") in ("image", "pdf")] if messages else []
        tools = (
            ["--tools", "Read", "--allowedTools", "Read", "--add-dir", str(Path(binary[0]["path"]).parent)]
            if binary
            else ["--tools", ""]
        )  # Read only, and only this chat's folder
        if binary:
            messages = messages[:-1] + [
                {
                    **messages[-1],
                    "text": messages[-1]["text"] + "\n\n[Прикреплены файлы — открой их "
                    "инструментом Read: " + "; ".join(f["path"] for f in binary) + "]",
                }
            ]
        args = [
            exe,
            "-p",
            "--output-format",
            "stream-json",
            "--verbose",
            "--include-partial-messages",
            "--no-session-persistence",
            *tools,
            "--setting-sources",
            "",
            "--strict-mcp-config",
            "--system-prompt-file",
            sp_path,
        ] + (["--model", model] if model else [])
        p = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=net.env(
                {
                    **claude_settings_env(),  # a proxy/subscription configured in Claude Code keeps working
                    "GIT_CEILING_DIRECTORIES": str(cwd.parent),
                    "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",  # no notes of its own about the owner
                    # the same longest answer as every other model (Настройки → Движок)
                    "CLAUDE_CODE_MAX_OUTPUT_TOKENS": str(_tuning.get(vault)["answer"]),
                }
            ),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        p.stdin.write(_flatten(system, messages).encode("utf-8"))
        p.stdin.close()
        got = False
        # never hang: no first word in 90 s or a pause over 180 s → stop and say why
        watch = {"last": time.time(), "killed": False}

        def watchdog():
            while p.poll() is None:
                if time.time() - watch["last"] > (180 if got else 90):
                    watch["killed"] = True
                    p.kill()
                    return
                time.sleep(1)

        threading.Thread(target=watchdog, daemon=True).start()
        try:
            for raw in p.stdout:
                watch["last"] = time.time()
                if stop and stop():
                    p.kill()
                    return
                try:
                    d = json.loads(raw.decode("utf-8", "replace"))
                except ValueError:
                    continue
                if d.get("type") == "stream_event":
                    e = d.get("event", {})
                    if e.get("type") == "content_block_delta" and e.get("delta", {}).get("type") == "text_delta":
                        got = True
                        yield e["delta"]["text"]
                elif d.get("type") == "result":
                    u = d.get("usage") or {}
                    usage.update(
                        {
                            "in": int(u.get("input_tokens") or 0),
                            "out": int(u.get("output_tokens") or 0),
                            "cache": int(u.get("cache_read_input_tokens") or 0)
                            + int(u.get("cache_creation_input_tokens") or 0),
                        }
                    )
                    res = str(d.get("result") or "")
                    if d.get("is_error"):
                        raise claude_problem(res)
                    if not got and res:
                        e2 = claude_problem(res) if len(res) < 300 else None
                        if isinstance(e2, AccountProblem):  # the limit notice arrives as an ordinary answer
                            raise e2
                        yield res
                elif (
                    d.get("type") == "assistant" and not got and (d.get("message") or {}).get("model") == "<synthetic>"
                ):
                    parts = (d.get("message") or {}).get("content") or []
                    note = " ".join(str(x.get("text") or "") for x in parts if isinstance(x, dict))
                    if isinstance(claude_problem(note), AccountProblem):
                        raise claude_problem(note)
        finally:
            p.wait(timeout=30)
            try:
                os.remove(sp_path)
            except OSError:
                pass
        if watch["killed"]:
            raise RuntimeError("Claude не отвечает. Проверь интернет или прокси: Настройки → Прокси")
        if p.returncode not in (0, None) and not got:
            raise claude_problem(p.stderr.read().decode("utf-8", "replace")[:300] or "Claude Code завершился с ошибкой")
        return

    if pid == "local":
        from .. import localllm

        port = localllm.ensure_server(model, vault)  # starts the built-in engine on first use
        base, key, model = f"http://127.0.0.1:{port}/v1", "local", model or "local"
    else:
        base, key = base_of(vault, pid), key_of(vault, pid)
    if PROVIDERS[pid]["key"] and not key:
        raise NotSent(f"Нет ключа {PROVIDERS[pid]['name']}: добавь его в настройках")
    folder = folder_of(vault) if pid == "yandex" else ""
    if pid == "yandex" and not folder:
        raise NotSent("Нет ID каталога Yandex Cloud: добавь его в настройках")
    if not model:
        raise NotSent("Выбери модель")
    msgs = [{"role": m["role"], "content": _content(pid, m)} for m in messages]
    from .. import tuning

    cap = tuning.get(vault)["answer"]  # the longest answer the owner allows (Настройки → Движок)
    if pid in tuning.FREE:  # free on this computer; a thinking model needs room to reason
        cap = max(cap, 2000)
    if pid == "anthropic":
        req = urllib.request.Request(
            base + "/v1/messages",
            method="POST",
            data=json.dumps(
                {"model": model, "max_tokens": cap, "system": system, "messages": msgs, "stream": True}
            ).encode(),
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        )
        finished = False
        for ev in _sse(req):
            if stop and stop():
                return
            if ev.get("type") == "message_stop":
                finished = True
            if ev.get("type") == "content_block_delta" and ev.get("delta", {}).get("type") == "text_delta":
                yield ev["delta"]["text"]
            elif ev.get("type") == "message_start":
                u = (ev.get("message") or {}).get("usage") or {}
                usage.update(
                    {
                        "in": int(u.get("input_tokens") or 0),
                        "cache": int(u.get("cache_read_input_tokens") or 0)
                        + int(u.get("cache_creation_input_tokens") or 0),
                    }
                )
            elif ev.get("type") == "message_delta":
                usage["out"] = int((ev.get("usage") or {}).get("output_tokens") or 0)
            elif ev.get("type") == "error":
                from ..errors import http

                err = ev.get("error") or {}
                code = 529 if "overload" in str(err.get("type", "")) + str(err.get("message", "")).lower() else 502
                raise RuntimeError(http(code, json.dumps({"error": err}), "Claude", model))
        if not finished:
            from ..errors import Cut

            raise Cut("ответ оборвался")
        return
    if pid == "ollama":
        req = urllib.request.Request(
            base + "/api/chat",
            method="POST",
            data=json.dumps(
                {
                    "model": model,
                    "stream": True,
                    "options": {"num_predict": cap},
                    "messages": [{"role": "system", "content": system}]
                    + [
                        {
                            **mm,
                            **(
                                {
                                    "images": [
                                        __import__("mnema.chat.attach", fromlist=["b64"]).b64(f["path"])
                                        for f in (m.get("files") or [])
                                        if f.get("kind") == "image"
                                    ]
                                }
                                if any(f.get("kind") == "image" for f in (m.get("files") or []))
                                else {}
                            ),
                        }
                        for mm, m in zip(msgs, messages)
                    ],
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
        )
        with net.urlopen(req, timeout=600) as r:
            for raw in r:
                if stop and stop():
                    return
                try:
                    d = json.loads(raw)
                except ValueError:
                    continue
                if d.get("error"):
                    raise RuntimeError(f"Ollama: {str(d['error'])[:200]}")
                piece = (d.get("message") or {}).get("content", "")
                if piece:
                    yield piece
                if d.get("done"):
                    usage.update({"in": int(d.get("prompt_eval_count") or 0), "out": int(d.get("eval_count") or 0)})
                    return
        from ..errors import Cut

        raise Cut("ответ оборвался")
    # OpenAI-compatible: OpenAI, Gemini, OpenRouter
    req = urllib.request.Request(
        base + "/chat/completions",
        method="POST",
        data=json.dumps(
            {
                "model": f"gpt://{folder}/{model}" if pid == "yandex" else model,
                "stream": True,
                "stream_options": {"include_usage": True},
                **({"max_completion_tokens": cap} if pid == "openai" else {"max_tokens": cap}),
                **(
                    {
                        "temperature": 0.3,
                        "stop": ["\nВладелец", "\n[Владелец", "\nПользователь:", "\nUser:"],
                        "return_progress": True,
                    }  # how much of the prompt it has read: shown to the owner
                    if pid == "local"
                    else {}
                ),  # small local models: less invention, never speak for the owner
                "messages": [{"role": "system", "content": system}] + msgs,
            }
        ).encode(),
        headers=_opencode_headers(key, str((meta or {}).get("chat") or "mnemai-default"))
        if pid == "opencode_go"
        else _yandex_headers(key, folder)
        if pid == "yandex"
        else {"Authorization": f"Bearer {key or 'local'}", "Content-Type": "application/json"},
    )
    finished = False
    for ev in _sse(req):
        if stop and stop():
            return
        if ev.get("_done"):
            finished = True
            continue
        if ev.get("error"):  # an error inside the stream (OpenRouter, Gemini): not a quiet end
            from ..errors import http

            err = ev["error"] if isinstance(ev["error"], dict) else {"message": str(ev["error"])}
            raise RuntimeError(
                http(
                    int(err.get("code") or 502) if str(err.get("code", "")).isdigit() else 502,
                    json.dumps({"error": err}),
                    PROVIDERS[pid]["name"],
                    model,
                )
            )
        if ev.get("usage"):
            finished = True
        pp = ev.get("prompt_progress")
        if pp and pp.get("total"):
            done = int(pp.get("processed") or 0)
            usage["progress"] = {
                "part": min(1.0, done / pp["total"]),
                "ms": int(pp.get("time_ms") or 0),
                "done": done,
                "total": int(pp["total"]),
            }
        if ev.get("usage"):
            u = ev["usage"]
            usage.update({"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)})
        for ch in ev.get("choices") or []:
            if ch.get("finish_reason"):
                finished = True
            if (ch.get("delta") or {}).get(
                "reasoning_content"
            ):  # a thinking model reasons first; hidden from the owner
                usage["reasoning"] = usage.get("reasoning", 0) + len(ch["delta"]["reasoning_content"])
            piece = (ch.get("delta") or {}).get("content")
            if piece:
                yield piece
    if not finished:
        from ..errors import Cut

        raise Cut("ответ оборвался")


def _content(pid: str, m: dict):
    """Message content with images / PDF in the provider's own format."""
    from .attach import b64

    files = [f for f in (m.get("files") or []) if f.get("kind") in ("image", "pdf")]
    if not files:
        return m["text"]
    if pid == "anthropic":
        blocks = [
            {
                "type": "image" if f["kind"] == "image" else "document",
                "source": {"type": "base64", "media_type": f["mime"], "data": b64(f["path"])},
            }
            for f in files
        ]
        return blocks + [{"type": "text", "text": m["text"]}]
    if any(f["kind"] == "pdf" for f in files):
        raise RuntimeError(
            "В этом PDF не нашлось текста: ни текстового слоя, ни читаемого скана. Пришли его картинками страниц или текстом"
        )
    if pid == "ollama":
        return m["text"]  # images go into the separate "images" field
    return [{"type": "text", "text": m["text"]}] + [
        {"type": "image_url", "image_url": {"url": f"data:{f['mime']};base64,{b64(f['path'])}"}} for f in files
    ]


def complete(
    vault: Vault,
    pid: str,
    model: str,
    system: str,
    messages: list[dict],
    usage: dict | None = None,
    meta: dict | None = None,
) -> str:
    return "".join(stream(vault, pid, model, system, messages, usage=usage, meta=meta))
