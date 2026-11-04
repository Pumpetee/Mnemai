"""API for the wrapper: chats, models and keys, the behavior profile, the live learning feed."""

from __future__ import annotations

from . import net
from .agent import profile as P
from .chat import engine as CH, providers as PR
from .learn import engine as LE, settings as S
from .vault import Vault


_OFFER_LOCK = __import__("threading").Lock()


def _web():
    from . import web

    return web


def get(vault: Vault, path: str, q: dict):
    if path == "/api/chats":
        return 200, {
            "chats": CH.list_chats(vault, q=q.get("q", ""), sort=q.get("sort", "date")),
            "default_model": CH.default_model(vault),
            "session": CH.current_session(vault),
            "session_names": CH.session_names(vault),
        }
    if path == "/api/knowledge":  # «Справочник Mnemai»: the knowledge base, section by section
        from .chat.selfknow import kb_sections

        return 200, {"sections": [{"title": t, "text": x} for t, x in kb_sections()]}
    if path == "/api/chat/export":
        from . import achievements

        achievements.event(vault, "exports")
        return 200, {"markdown": CH.export_chat(vault, q.get("id", ""))}
    if path == "/api/chat/sees":
        return 200, sees(vault, q.get("model", ""))
    if path == "/api/chat":
        return 200, CH.load_chat(vault, q.get("id", ""))
    if path == "/api/vpn":
        from . import vpnkey

        return 200, vpnkey.status(vault)
    if path == "/api/connect":
        from . import cli

        return 200, cli.connected()
    if path == "/api/chat/poll":
        return 200, CH.state(q.get("id", ""))
    if path == "/api/ach":
        from . import achievements

        return 200, achievements.summary(vault)
    if path == "/api/prompts":
        from .chat import prompts as PRM

        return 200, {"prompts": PRM.all_prompts(vault), **PRM.settings(vault)}
    if path == "/api/models":
        PR.find_strata(vault)  # once per start: a Strata already running on this computer shows up by itself
        return 200, {"providers": PR.status(vault), "default_model": CH.default_model(vault)}
    if path == "/api/agent":
        prof = P.load(vault)
        return 200, {
            "catalog": P.catalog_view(prof),
            "presets": {k: {"name": v["name"], "note": v["note"]} for k, v in P.PRESETS.items()},
            "simple": P.SIMPLE,
            "profile": prof,
            "proxy_system": net.system_proxy(),
            "proxy_used": net.describe(),
            "proxy_password_set": bool(net.stored_password(vault)),
            "brave_set": bool(_web().brave_key()),
        }
    if path == "/api/agent/pack":
        return 200, P.export_pack(P.load(vault), q.get("name", "Мой набор"))
    if path == "/api/learn/live":
        return 200, {"events": LE.live(vault, q.get("since", ""))}
    if path == "/api/local":
        from . import localllm

        if q.get("probe"):
            localllm.probe_speed()
        return 200, {**localllm.status(), "offer": P.load(vault).get("local_offer", "")}
    if path == "/api/sync":
        from . import sync

        return 200, sync.public(vault)
    if path == "/api/local/heat":
        from . import heat

        return 200, heat.status()
    if path == "/api/net/detect":
        from . import vpn_detect

        return 200, vpn_detect.detect()
    if path == "/api/efs":
        from . import efs

        return 200, efs.status(vault)
    if path == "/api/crypto":
        from . import crypt

        return 200, crypt.status(vault.root)
    if path == "/api/crypto/key":  # the console helper (MCP) of this computer asks the running Mnemai
        from . import crypt

        return 200, {"key": crypt.key_b64(vault.root)}
    if path == "/api/scribe/settings":
        return 200, scribe_settings(vault)
    if path == "/api/scribe/status":
        from . import scribe

        return 200, scribe.status(vault)
    if path == "/api/memory/status":
        return 200, memory_status(vault)
    if path == "/api/outgoing":
        from . import outgoing as OG

        return 200, {
            **OG.report(vault, max(1, min(90, int(q.get("days", 7))))),
            "redact": bool(P.load(vault).get("redact", True)),
        }
    if path == "/api/telegram":  # the owner's Telegram, read only
        from .learn import tg_api

        return 200, tg_api.status(vault)
    if path == "/api/quiz":  # «Насколько Mnemai тебя знает»: facts from the memory, one by one
        from . import play

        return 200, play.quiz(vault)
    if path == "/api/interview":  # «Знакомство»: the questions
        from . import play

        return 200, {"questions": [{"key": k, "q": q, "eg": eg} for k, q, eg in play.INTERVIEW]}
    if path == "/api/telegram/chats":  # the owner's chats to pick from
        from .learn import tg_api

        return 200, {"chats": tg_api.dialogs(vault)}
    if path == "/api/obsidian":  # the Obsidian vaults on this computer, for «Подключить Obsidian»
        from . import extra

        mine = extra.folders(P.load(vault))
        return 200, {
            "vaults": [{**v, "added": v["path"] in mine} for v in extra.obsidian_vaults(vault)],
            "folders": [{"path": p, "obsidian": extra.is_obsidian(__import__("pathlib").Path(p))} for p in mine],
        }
    if path == "/api/engine":
        from . import tuning

        return 200, {
            **tuning.get(vault),
            "usage": tuning.month_usage(vault),
            "presets": tuning.PRESETS,
            "limits": tuning.LIMITS,
        }
    if path == "/api/learn/brain":
        return 200, brain_status(vault)
    if path == "/api/memory/why":
        return 200, why(vault, q.get("text", ""))
    return None


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
    if path == "/api/chat/send":
        return 200, CH.send(
            vault,
            str(b.get("text", "")),
            str(b.get("chat", "")),
            str(b.get("model", "")),
            files=b.get("files") or None,
            quote=str(b.get("quote", "")),
            web=bool(b["web"]) if "web" in b else None,
            consortium=b.get("consortium") or None,
            terms=bool(b["terms"]) if "terms" in b else None,
            opener=bool(b.get("opener")),
            private=bool(b["private"]) if "private" in b else None,
        )
    if path == "/api/chat/redo":
        return 200, CH.redo(vault, str(b.get("chat", "")), bool(b.get("web", True)))
    if path == "/api/chat/useful":
        return 200, CH.mark_useful(vault, str(b.get("chat", "")), int(b.get("index", -1)), bool(b.get("on", True)))
    if path == "/api/portrait/refresh":
        from . import portrait
        from .memory import generate_now

        r = portrait.refresh(vault, force=bool(b.get("force")))
        if r["written"]:
            generate_now(vault)
        return 200, r
    if path == "/api/session/new":
        return 200, CH.new_session(vault)
    if path == "/api/session/rename":
        return 200, {"names": CH.rename_session(vault, str(b.get("id", "")), str(b.get("name", "")))}
    if path == "/api/session/delete":
        return 200, {"deleted": CH.delete_session(vault, str(b.get("id", "")))}
    if path == "/api/chat/learn_now":
        return 200, CH.learn_chat_now(vault, str(b.get("id", "")))
    if path == "/api/chat/update":
        return 200, CH.update_chat(
            vault,
            str(b.get("id", "")),
            b.get("title"),
            b.get("pinned") if "pinned" in b else None,
            b.get("private") if "private" in b else None,
            b.get("consortium") if "consortium" in b else None,
        )
    if path == "/api/chat/regenerate":
        return 200, CH.regenerate(vault, str(b.get("chat", "")), str(b.get("model", "")))
    if path == "/api/chat/cons":
        from .chat import consortium as CO

        return 200, CO.control(
            vault,
            str(b.get("chat", "")),
            str(b.get("action", "")),
            b.get("members"),
            int(b["rounds"]) if b.get("rounds") else None,
            str(b.get("model", "")),
            {k: b.get(k) for k in ("format", "roles", "summarizer", "length", "search", "challenge")},
        )
    if path == "/api/vpn":  # a VPN key: Mnemai connects through it itself (vpnkey.py)
        from . import vpnkey

        a = str(b.get("action", ""))
        if a == "connect":
            return 200, {
                **vpnkey.connect(vault, str(b.get("key", "")), str(b.get("service", ""))),
                **vpnkey.status(vault),
            }
        if a == "off":
            return 200, vpnkey.disconnect(vault)
        raise ValueError("неизвестное действие")
    if path == "/api/web/page":  # the paper clip → «Страницу по ссылке»
        from . import web

        url = str(b.get("url", "")).strip()
        if not url.startswith(("http://", "https://")):
            raise ValueError("нужна ссылка, начинающаяся с http")
        try:
            d = web.fetch(url)
        except Exception as e:
            raise ValueError(f"не открылась страница: {str(e)[:160]}")
        if not (d.get("text") or "").strip():
            raise ValueError("на странице нет текста, который можно прочитать")
        return 200, {"url": d["url"], "title": d.get("title") or url, "text": d["text"][:120_000]}
    if path == "/api/chat/action":  # the owner's word on an action the model asked for
        return 200, CH.answer_action(str(b.get("chat", "")), str(b.get("id", "")), str(b.get("choice", "")))
    if path == "/api/files/open":  # «Открыть» a document the AI made: in its own program
        from .chat import tools as TL

        from . import osapi

        p = TL.resolve(vault, str(b.get("path", "")))
        if not p.is_file():
            return 404, {"error": "Файла нет: его переместили или удалили"}
        if p.suffix.lower() not in TL.OPENABLE:
            return 400, {"error": "Такой файл открывается только из папки: «Показать в папке»"}
        osapi.open_path(p)
        return 200, {"ok": True}
    if path == "/api/files/reveal":  # «Показать в папке» under an action
        import os

        from .chat import tools as TL

        from . import osapi

        p = TL.resolve(vault, str(b.get("path", "")))
        osapi.reveal(p) if p.is_file() else osapi.open_path(p)
        return 200, {"ok": True}
    if path == "/api/chat/stop":
        CH.stop(str(b.get("chat", "")))
        return 200, {"ok": True}
    if path == "/api/chat/delete":
        CH.delete_chat(vault, str(b.get("id", "")))
        return 200, {"ok": True}
    if path == "/api/providers":
        PR.save(
            vault,
            str(b.get("id", "")),
            endpoint=b.get("endpoint"),
            key=b.get("key"),
            disabled=bool(b["disabled"]) if "disabled" in b else None,
            folder=b.get("folder"),
        )
        return 200, {"providers": PR.status(vault)}
    if path == "/api/providers/claude_login":  # «Войти»: Claude Code in a terminal, it asks for the sign-in itself
        return 200, PR.claude_login()
    if path == "/api/providers/codex_login":
        return 200, PR.codex_login(vault)
    if path == "/api/providers/check":  # «Проверить снова»: a tiny real request to this AI
        r = PR.check(vault, str(b.get("id", "")))
        return 200, {**r, "providers": PR.status(vault)}
    if path == "/api/providers/models":
        try:
            ids = PR.fetch_models(vault, str(b.get("id", "")))
        except Exception as e:
            from . import errors as E

            pid = str(b.get("id", ""))
            msg = E.human(e, E.provider_name(pid), vpn=E.vpn_name(vault))
            if E.account_problem(e):  # a refused key is not «подключено»
                PR.note_problem(vault, pid, msg)
            return 200, {"ok": False, "error": msg, "providers": PR.status(vault)}
        return 200, {"ok": True, "models": ids, "providers": PR.status(vault)}
    if path == "/api/telegram":  # the owner's chats through the Telegram API, read only: login, code, password, forget
        from .learn import tg_api

        return 200, tg_api.configure(vault, b)
    if path == "/api/compare":  # «С памятью и без»: the same question, a plain chat and Mnemai, side by side
        from . import play

        return 200, play.compare(vault, str(b.get("question") or ""), b.get("models") or None)
    if path == "/api/quiz":  # an answer in the quiz fixes the memory: yes | changed | no
        from . import play

        return 200, play.quiz_answer(
            vault, str(b.get("id") or ""), str(b.get("verdict") or ""), str(b.get("text") or "")
        )
    if path == "/api/interview":  # «Знакомство»: the answers become ordinary facts
        from . import play

        return 200, play.interview_save(vault, b.get("answers") or {})
    if path == "/api/share/save":  # «Поделиться»: the card as a picture in Pictures/Mnemai, shown in its folder
        import base64
        import re as _re
        import time as _time
        from pathlib import Path as _P

        from . import osapi

        data = base64.b64decode(str(b.get("png") or "").split(",", 1)[-1])
        if not data.startswith(b"\x89PNG"):
            raise ValueError("это не картинка")
        folder = _P.home() / "Pictures" / "Mnemai"
        folder.mkdir(parents=True, exist_ok=True)
        name = _re.sub(r"[^\w -]+", "", str(b.get("name") or "mnemai"))[:40].strip() or "mnemai"
        p = folder / f"{name} {_time.strftime('%Y-%m-%d %H-%M-%S')}.png"
        p.write_bytes(data)
        osapi.reveal(p)
        return 200, {"ok": True, "path": str(p)}
    if path == "/api/settings/reset":  # Движок, Записи встреч, Программа back to the defaults
        from . import tuning

        tuning.save(vault, {"mode": "balance", "month": 0})
        d = P.DEFAULT
        P.save(
            vault,
            {k: d[k] for k in ("economy", "scribe_mode", "scribe_model", "scribe_keep_audio", "tools", "tools_ask")},
        )
        return 200, {"ok": True}
    if path == "/api/agent":
        if b.get("preset"):
            P.apply_preset(vault, str(b["preset"]))
        patch = {
            k: v
            for k, v in b.items()
            if k
            in (
                "toggles",
                "simple",
                "custom",
                "default_model",
                "team_vault",
                "extra_folders",
                "self_ask",
                "scribe_model",
                "local_offer",
                "economy",
                "web",
                "terms",
                "prompts_mode",
                "prompts_auto",
                "lang",
                "gender",
                "owner_name",
                "redact",
                "scribe_keep_audio",
                "scribe_summary_model",
                "last_model",
                "tools",
                "tool_folders",
                "tools_ask",
                "memory_on",
                "memory_asked",
            )
        }
        for k in ("default_model", "last_model", "scribe_model", "scribe_summary_model"):
            if "[object" in str(patch.get(k) or ""):  # a broken pick from the page is never remembered
                patch.pop(k)
        prof = P.save(vault, patch) if patch else P.load(vault)
        if "extra_folders" in patch:  # a folder just added is read in the background
            from . import extra

            extra.warm_all(vault)
        if "proxy" in b:  # address in the profile, password in the Windows secret store
            net.save(vault, str(b.get("proxy") or ""), b.get("proxy_password") if "proxy_password" in b else None)
            prof = P.load(vault)
        if "brave_key" in b:  # optional search key: kept outside the vault, like the AI keys
            from . import web
            from .learn import secrets_store
            from .learn.settings import _vid

            secrets_store.put(_vid(vault), "web.brave", str(b["brave_key"] or "").strip())
            web.set_brave_key(str(b["brave_key"] or ""))
        auto = (b.get("simple") or {}).get("autonomy")
        if auto in S.MODES:  # one slider sets how every source learns
            s = S.load(vault)
            if not s.get("demo"):
                for sid, src in s["sources"].items():
                    src["mode"] = auto if sid != "browser_history" or auto == "observe" else src["mode"]
                S.save(vault, s)
        return 200, {"profile": prof, "catalog": P.catalog_view(prof)}
    if path == "/api/net/check":
        pw = b.get("password")
        return 200, net.check(str(b.get("proxy", "")), net.stored_password(vault) if pw is None else str(pw))
    if path.startswith("/api/local/"):
        from . import localllm

        what = path.rsplit("/", 1)[-1]
        if what == "download":
            return 200, localllm.start_download(str(b.get("id", "")))
        if what == "pause":
            return 200, localllm.pause_download()
        if what == "cancel":
            return 200, localllm.cancel_download()
        if what == "delete":
            localllm.delete_model(str(b.get("id", "")))
            return 200, {"ok": True}
        if what == "probe":
            return 200, localllm.probe_speed(force=True)
        if what == "warm":
            from .chat import small

            mid = str(b.get("model", "")).partition(":")[2] or str(b.get("model", ""))
            return 200, small.warm(vault, mid) if small.is_small("local", mid) else {"ready": True, "skipped": True}
        if what == "cool":
            from . import heat

            return 200, heat.cool_down(vault)
        if what == "stop":
            from . import heat

            return 200, heat.stop_model()
        if what == "add_file":
            return 200, localllm.add_custom_file(str(b.get("path", "")))
        if what == "add_url":
            m = localllm.add_custom_url(str(b.get("url", "")))
            return 200, localllm.start_download(m["id"])
        if what == "offer":
            if b.get("claim"):  # the welcome is shown once, whatever loads the page twice
                with _OFFER_LOCK:
                    if P.load(vault).get("local_offer"):
                        return 200, {"claimed": False}
                    P.save(vault, {"local_offer": "shown"})
                return 200, {"claimed": True}
            P.save(vault, {"local_offer": str(b.get("state", "dismissed"))})
            return 200, {"ok": True}
    if path == "/api/ach/seen":
        from . import achievements

        achievements.seen(vault)
        return 200, {"ok": True}
    if path == "/api/ach/event":
        return 200, {"ok": True}  # counted by achievements.on_post
    if path == "/api/engine":
        from . import tuning

        return 200, {**tuning.save(vault, b), "usage": tuning.month_usage(vault)}
    if path == "/api/crypto":
        return crypto_post(vault, b)
    if path == "/api/efs":
        from . import efs

        what = str(b.get("action", ""))
        if what == "on":
            return 200, efs.enable(vault)
        if what == "off":
            return 200, efs.disable(vault)
        if what == "backup":
            return 200, {**efs.status(vault), "file": efs.backup_key()}
        return 200, efs.status(vault)
    if path.startswith("/api/sync/"):
        from . import sync

        what = path.rsplit("/", 1)[-1]
        if what == "add":
            sync.add(
                vault, str(b.get("kind", "")), str(b.get("path", "")), str(b.get("url", "")), str(b.get("token", ""))
            )
        elif what == "remove":
            sync.remove(vault, str(b.get("id", "")))
        elif what == "minutes":
            sync.set_minutes(vault, int(b.get("minutes") or 10))
        elif what == "now":
            return 200, {**sync.public(vault), "result": sync.run(vault, str(b.get("id", "")))}
        return 200, sync.public(vault)
    if path == "/api/chat/self_ask":
        return 200, CH.answer_self_ask(
            vault, str(b.get("chat", "")), int(b.get("i", -1)), str(b.get("action", "skip")), str(b.get("text", ""))
        )
    if path == "/api/prompts/answer":
        return 200, CH.answer_offer(vault, str(b.get("chat", "")), str(b.get("choice", "skip")))
    if path == "/api/prompts/delete":
        from .chat import prompts as PRM

        PRM.delete(vault, str(b.get("file", "")))
        return 200, {"prompts": PRM.all_prompts(vault)}
    if path == "/api/prompts/open":
        import os
        from .chat import prompts as PRM

        from . import osapi

        f = PRM.folder(vault) / os.path.basename(str(b.get("file", "")))
        osapi.open_path(f if f.exists() else PRM.folder(vault))
        return 200, {"ok": True}
    if path.startswith("/api/voice/"):  # voice command: microphone → text, on this computer
        from . import voice

        what = path.rsplit("/", 1)[-1]
        if what == "start":
            return 200, voice.start(vault)
        if what == "stop":
            return 200, voice.stop(vault, str(b.get("lang", "")))
        return 200, voice.cancel()
    if path.startswith("/api/scribe/"):
        from . import scribe

        what = path.rsplit("/", 1)[-1]
        if what == "start":
            return 200, scribe.start(vault, str(b.get("name", "")))
        if what == "stop":
            return 200, scribe.stop(vault, str(b.get("model", "")))
        if what == "import":
            return 200, scribe.import_file(
                vault,
                str(b.get("filename", "")),
                str(b.get("data", "")),
                str(b.get("name", "")),
                str(b.get("model", "")),
            )
        if what == "reset":
            scribe.st(vault).update(status="idle")
            return 200, scribe.status(vault)
        if what == "answer":  # cloud or this computer, asked when the computer is slow
            s = scribe.st(vault)
            choice = "cloud" if b.get("choice") == "cloud" else "local"
            if b.get("remember"):
                P.save(vault, {"scribe_mode": "partial" if choice == "cloud" else "local"})
            s["choice"] = choice
            if s.get("_answer"):
                s["_answer"].set()
            return 200, scribe.status(vault)
        if what == "settings":
            from . import scribe_cloud as SC
            from .learn import secrets_store
            from .learn.settings import _vid

            patch = {}
            if b.get("mode") in SC.MODES:
                patch["scribe_mode"] = b["mode"]
            if "model" in b and b["model"] in ("auto", "small", "medium", "large-v3"):
                patch["scribe_model"] = b["model"]
            if "base" in b:
                patch["scribe_base"] = str(b["base"]).strip()
            if "cloud_model" in b:
                patch["scribe_cloud_model"] = str(b["cloud_model"]).strip()
            if b.get("key"):
                secrets_store.put(_vid(vault), "scribe.cloud", str(b["key"]).strip())
            if patch:
                P.save(vault, patch)
            return 200, scribe_settings(vault)
    if path == "/api/import/chatgpt":
        import base64

        raw = base64.b64decode(str(b.get("data", "")).split(",")[-1])
        name = str(b.get("filename", "conversations.json"))
        dest = vault.service / "imports"
        dest.mkdir(parents=True, exist_ok=True)
        if name.lower().endswith(".zip"):  # the whole ChatGPT export archive
            import io
            import zipfile

            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                member = next((n for n in z.namelist() if n.endswith("conversations.json")), None)
                if not member:
                    return 400, {"error": "в архиве нет conversations.json"}
                raw = z.read(member)
        import json as _json

        try:
            convs = _json.loads(raw.decode("utf-8"))
        except ValueError:
            return 400, {"error": "это не выгрузка ChatGPT"}
        (dest / "conversations.json").write_bytes(raw)
        s = S.load(vault)
        if s.get("demo"):
            return 403, {"error": "в демо обучение выключено"}
        s["sources"]["chatgpt_export"].update(
            enabled=True,
            options={**s["sources"]["chatgpt_export"]["options"], "path": str(dest / "conversations.json")},
        )
        S.save(vault, s)
        from .api_learn import start_run

        start_run(vault, initial=True, only=["chatgpt_export"])
        return 200, {"ok": True, "conversations": len(convs) if isinstance(convs, list) else 0}
    if path == "/api/open_url":
        import webbrowser

        url = str(b.get("url", ""))
        allowed = (
            "https://platform.openai.com/",
            "https://aistudio.google.com",
            "https://openrouter.ai/",
            "https://ollama.com",
            "https://auth.openai.com/api/accounts/authorize?",
            "https://developers.openai.com/siwc/",
            "https://developers.openai.com/codex/cli",
            "https://opencode.ai/console/go",
        )
        if not url.startswith(allowed):
            return 400, {"error": "этот адрес не открываю"}
        webbrowser.open(url)  # the owner's normal browser
        return 200, {"ok": True}
    if path == "/api/memory/open":
        import os

        from . import osapi

        target = vault.root
        osapi.open_path(target)  # Explorer, Finder or the file manager on the memory folder
        return 200, {"ok": True, "folder": str(target)}
    if path == "/api/connect":
        from . import cli

        target = str(b.get("target", ""))
        if target not in ("claude-code", "claude-desktop", "cursor"):
            return 400, {"error": "неизвестная цель"}
        said, orig = [], cli.out
        cli.out = said.append  # the windowed app has no console
        try:
            cli.install(target, vault, True, None)
        except SystemExit as e:
            return 200, {"ok": False, "message": str(e)}
        except Exception as e:
            return 200, {"ok": False, "message": str(e)[:300]}
        finally:
            cli.out = orig
        return 200, {"ok": True, "message": "\n".join(said)[-400:]}
    if path == "/api/agent/pack":
        prof = P.import_pack(vault, b)
        return 200, {"profile": prof, "catalog": P.catalog_view(prof)}
    return None


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
