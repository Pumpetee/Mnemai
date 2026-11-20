"""API для обёртки: чаты, модели и ключи, профиль поведения, живой фид обучения.

Все маршруты «if path == ...» перенесены в декларативный роутер (mnema/http_router.py);
здесь остались вспомогательные функции application-слоя и точки вызова get/post для тестов.
"""

from __future__ import annotations

from . import net
from .agent import profile as P
from .chat import engine as CH, providers as PR
from .learn import settings as S
from .vault import Vault


def _web():
    from . import web

    return web


def get(vault: Vault, path: str, q: dict):
    """GET-маршруты чата: делегирование декларативному роутеру (прежняя точка вызова)."""
    from .http_router import dispatch

    return dispatch(vault, "GET", path, q, None)


def memory_status(vault: Vault) -> dict:
    """Where the memory lives and its timers: last change, last and next check of the sources."""
    import datetime as dt

    try:  # facts that came by hand or by import: the portrait is built from them too, not only after learning
        from . import portrait

        if portrait.due(vault):
            import threading

            threading.Thread(target=lambda: portrait.refresh(vault), daemon=True, name="mnema-portrait").start()
    except Exception:
        pass

    files = [p for p in vault.root.rglob("*.md") if ".mnema" not in p.parts]
    last = max((p.stat().st_mtime for p in files), default=0)
    lf = vault.service / "learn"
    read = lambda n: (lf / n).read_text(encoding="utf-8").strip() if (lf / n).exists() else ""  # noqa: E731
    s = S.load(vault)
    background = [S.SOURCES[k]["name"] for k, x in s["sources"].items() if x.get("enabled") and k != "mnema_chat"]
    chats = len(list((vault.service / "chats").glob("*.json"))) if (vault.service / "chats").exists() else 0
    return {
        "folder": str(vault.root),
        "files": len(files),
        "chats": chats,
        "updated": dt.datetime.fromtimestamp(last).isoformat(timespec="seconds") if last else "",
        "last_check": read("last_check"),
        "next_check": read("next_check") if background and not s["paused"] else "",
        "interval": s["interval_minutes"],
        "background": background,
        "paused": s["paused"],
        "demo": bool(s.get("demo")),
        "chat_learning": bool(s["sources"].get("mnema_chat", {}).get("enabled")),
        "safety": safety(vault),
    }


def scribe_settings(vault: Vault) -> dict:
    from . import scribe, scribe_cloud as SC

    s, c = SC.settings(vault), SC.creds(vault)
    return {
        **s,
        "quality": P.load(vault).get("scribe_model") or "auto",
        "cloud_ready": bool(c),
        "cloud_from": ("свой адрес" if s["base"] else "ключ OpenAI") if c else "",
        "local_model": scribe.model_name(vault),
    }


def safety(vault: Vault) -> dict:
    """What protects the owner's data right now — only facts the program can check."""
    from .clients import load_clients
    from .journal import events
    from .learn import secrets_store
    from .learn.settings import _vid

    clients = list(load_clients(vault).values())
    guarded = [c.name for c in clients if set(c.deny_tags or []) & {"money", "health", "private"}]
    try:
        keys = len(secrets_store._load().get(_vid(vault), {}))
    except Exception:
        keys = 0
    try:
        undo = len(events(vault, limit=10000))
    except Exception:
        undo = 0
    from . import outgoing as OG

    week = OG.report(vault, 7)
    from . import efs

    return {
        "guarded": guarded,
        "ais": len(clients),
        "keys": keys,
        "undo": undo,
        "proxy": net.describe(),
        "encrypted": efs.status(vault)["on"],
        "redact": bool(P.load(vault).get("redact", True)),
        "out_requests": week["requests"],
        "out_redacted": sum(week["redacted"].values()),
    }


def brain_status(vault: Vault) -> dict:
    """Can learning actually understand speech right now? Checked for real, quickly."""
    s = S.load(vault)
    b = s["brain"]
    auto = b.get("kind") == "auto"
    kind = S.resolve_brain(s)
    st = _brain_status(b, kind, vault)
    if auto:
        st["auto"] = True
        if kind == "none":
            st["message"] = (
                "Сама выбираю, чем понимать речь, но пока нечем: не подключено ни одной модели. "
                "Понимаю только явное: «запомни», поправки, решения."
            )
        elif st["ok"]:
            st["message"] += " Выбрано автоматически."
    st["kind"] = "auto" if auto else kind
    st["using"] = kind
    return st


def _brain_status(b: dict, kind: str, vault: Vault | None = None) -> dict:
    if kind == "model":
        ref = CH.default_model(vault) if vault else ""
        ready = {p["id"]: p["ready"] for p in PR.status(vault)} if vault else {}
        ok = bool(ref) and ready.get(ref.partition(":")[0], False)
        from .chat.consortium import speaker_name

        return {
            "kind": kind,
            "ok": ok,
            "level": "ok" if ok else "info",
            "message": f"Понимаю речь через модель, с которой ты говоришь: {speaker_name(ref)}."
            if ok
            else "Понимаю только явное: «запомни», поправки, решения. Подключи любую модель — и буду понимать речь.",
        }

    if kind == "none":
        return {
            "kind": kind,
            "ok": False,
            "level": "info",
            "message": "Понимаю только явное: «запомни», поправки, решения. Обычную речь не разбираю.",
        }
    if kind == "claude_code":
        from .learn.brains import claude_signed_in

        ok = claude_signed_in() and any(p["id"] == "claude_code" and p["ready"] for p in PR.status(vault))
        return {
            "kind": kind,
            "ok": ok,
            "level": "ok" if ok else "bad",
            "message": "Понимаю речь через Claude по подписке."
            if ok
            else "Claude Code не найден на компьютере или в него не выполнен вход.",
        }
    if kind == "ollama":
        if not b.get("model"):
            return {
                "kind": kind,
                "ok": False,
                "level": "bad",
                "message": "Выбрана локальная модель, но не указано какая.",
            }
        try:
            import urllib.request

            urllib.request.urlopen(
                (b.get("endpoint") or "http://127.0.0.1:11434").rstrip("/") + "/api/tags", timeout=1.5
            )
        except Exception:
            return {"kind": kind, "ok": False, "level": "bad", "message": "Ollama не запущена — обучение не работает."}
        return {"kind": kind, "ok": True, "level": "ok", "message": f"Понимаю речь локально: {b['model']}."}
    if kind == "local":
        from . import localllm

        inst = localllm.installed_models()
        return {
            "kind": kind,
            "ok": bool(inst),
            "level": "ok" if inst else "bad",
            "message": f"Понимаю речь встроенной моделью {inst[0]['name']}."
            if inst
            else "Встроенная модель не скачана: Настройки → Локальная модель.",
        }
    ok = bool(b.get("api_key") and b.get("model"))
    return {
        "kind": kind,
        "ok": ok,
        "level": "ok" if ok else "bad",
        "message": "Понимаю речь через твой ключ." if ok else "Для своего ключа укажи ключ и модель.",
    }


def sees(vault: Vault, model: str) -> dict:
    """«Что видит модель»: which parts of memory this model gets, what's hidden, which rules apply."""
    from .clients import get_client
    from .learn.ledger import Ledger

    pid = (model or CH.default_model(vault)).partition(":")[0]
    pid = pid if pid in PR.PROVIDERS else "claude_code"
    c = get_client(vault, PR.PROVIDERS[pid]["client"])
    names = {
        "profile": "Обо мне",
        "rules": "Правила",
        "projects": "Проекты",
        "cards": "Карточки",
        "people": "Люди",
        "decisions": "События и решения",
        "inbox": "Входящие",
    }
    counts = {}
    for scope in names:
        notes = vault.by_scope(scope)
        counts[scope] = (
            sum(sum(1 for l in (vault.read_raw(n.rel) or "").splitlines() if l.strip().startswith("- ")) for n in notes)
            if scope not in ("projects", "people", "cards")
            else len(notes)
        )
    prof = P.load(vault)
    eff = P.effective(prof)
    return {
        "provider": PR.PROVIDERS[pid]["name"],
        "client": c.name,
        "sees": [{"id": k, "name": v, "count": counts[k]} for k, v in names.items() if c.allows(k)],
        "hidden_parts": [v for k, v in names.items() if not c.allows(k)],
        "hidden_tags": [{"money": "деньги", "health": "здоровье", "private": "личное"}.get(t, t) for t in c.deny_tags],
        "preset": P.PRESETS.get(prof.get("preset") or "", {}).get("name", "свой"),
        "rules_on": sum(1 for v in eff.values() if v),
        "rules_total": len(eff),
        "second_pass": eff.get("second_pass", False),
        "ask_options": eff.get("ask_options", False),
        "learned": sum(1 for i in Ledger(vault).items if i["state"] in ("written", "confirmed")),
    }


def why(vault: Vault, text: str) -> dict:
    """«Откуда я это знаю»: the ledger entry behind a line of memory."""
    from .learn.ledger import Ledger, similar

    best, score = None, 0.0
    for it in Ledger(vault).items:
        sc = similar(text, it["text"])
        if sc > score:
            best, score = it, sc
    if not best or score < 0.7:
        return {"found": False}
    keys = (
        "id",
        "text",
        "kind",
        "tags",
        "confidence",
        "count",
        "sources",
        "evidence",
        "first_seen",
        "last_seen",
        "state",
        "why",
        "decided_by",
        "url",
    )
    out = {k: best.get(k) for k in keys}
    out["source_names"] = [S.SOURCES.get(x, {}).get("name", x) for x in best.get("sources", [])]
    out["found"] = True
    return out


def post(vault: Vault, path: str, b: dict):
    """POST-маршруты чата: делегирование декларативному роутеру (прежняя точка вызова)."""
    from .http_router import dispatch

    return dispatch(vault, "POST", path, {}, b)


def crypto_post(vault: Vault, b: dict):
    """Mnemai's own encryption: on, off, the password at start, a new password, remember on this computer."""
    from . import crypt
    from .api import APP_HOOKS

    what, pw = str(b.get("action", "")), str(b.get("password", ""))
    try:
        if what == "on":
            r = crypt.enable(vault.root, pw, bool(b.get("remember", True)))
        elif what == "off":
            r = crypt.disable(vault.root, pw)
        elif what == "unlock":
            crypt.unlock(vault.root, pw, bool(b.get("remember", False)))
            hook = APP_HOOKS.get("unlocked")
            if hook:
                hook()
            r = {}
        elif what == "password":
            crypt.change_password(vault.root, str(b.get("old", "")), str(b.get("new", "")))
            r = {}
        elif what == "remember":
            crypt.set_remember(vault.root, bool(b.get("on")))
            r = {}
        else:
            return 400, {"error": "такого действия нет"}
    except crypt.BadPassword:
        return 403, {"error": "Пароль не подходит"}
    except ValueError as e:
        return 400, {"error": str(e)}
    return 200, {**crypt.status(vault.root), **r}
