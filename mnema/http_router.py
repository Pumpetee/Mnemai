"""Декларативный роутер локального API: таблица Route(method, path, handler, request_schema, response_schema).

Сюда перенесены все ручные ветки «if path == ...» из api.py, api_chat.py и api_learn.py, включая
/api/ping и /api/app/* (маршруты-адаптеры окна: APP_HOOKS заполняет desktop, порт сервера — APP_PORT).
Обработчики — тонкие: валидируют входы через схемы и вызывают существующие функции application-слоя
(engine, tools, planner, memory и т.д.). Поведение 1:1 с прежним: те же пути, коды, JSON и тексты ошибок.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from typing import Any, Callable

from . import __version__, net
from .agent import profile as P
from .chat import engine as CH, providers as PR
from .clients import Client, load_clients, save_clients
from .http_schemas import RequestSchema, ResponseSchema, fields
from .journal import events, undo, write_with_journal
from .learn import engine as LE, settings as S
from .memory import context_for, generate_now, remember
from .vault import Vault

# заметки владельца, а не генерируемые слои (Now, Index), журнал, сейвы или служебные файлы
EDITABLE = re.compile(
    r"^(?!.*\.\.)(?!.*/\.)(00 Inbox/[^/]+|70 Memory/(Profile|Rules|Thoughts)|70 Memory/Cards/[^/]+|"
    r"20 Projects/[^/]+(/[^/]+)*|30 People/[^/]+|60 Events/[^/]+|80 Meetings/[^/]+(/[^/]+)?|"
    r"90 System/(?:Recipes|Prompts)/[^/]+)\.md$"
)

_OFFER_LOCK = threading.Lock()

APP_HOOKS: dict = {}  # filled by the desktop program: show, info, autostart, switch, ...
APP_PORT: int = 0  # the local server port (set by api.make_handler) for /api/app/* answers


def ok(payload: Any) -> tuple[int, Any]:
    return 200, payload


def err(code: int, message: str) -> tuple[int, dict]:
    return code, {"error": message}


@dataclass
class Route:
    method: str
    path: str
    handler: Callable[[Vault, "Ctx"], Any]
    request_schema: RequestSchema | None = None
    response_schema: ResponseSchema | None = None
    prefix: bool = False
    raw_body: bool = False  # обработчику нужен необработанный body (например, список для /api/clients)


@dataclass
class Ctx:
    path: str
    query: dict
    body: Any
    params: dict


def _web():
    from . import web

    return web


# -- GET-обработчики ---------------------------------------------------------


def _get_chats(vault: Vault, ctx: Ctx):
    p = ctx.params
    return ok(
        {
            "chats": CH.list_chats(vault, q=p["q"], sort=p["sort"]),
            "default_model": CH.default_model(vault),
            "session": CH.current_session(vault),
            "session_names": CH.session_names(vault),
        }
    )


def _get_knowledge(vault: Vault, ctx: Ctx):
    from .chat.selfknow import kb_sections

    return ok({"sections": [{"title": t, "text": x} for t, x in kb_sections()]})


def _get_chat_export(vault: Vault, ctx: Ctx):
    from . import achievements

    achievements.event(vault, "exports")
    return ok({"markdown": CH.export_chat(vault, ctx.params["id"])})


def _get_chat_sees(vault: Vault, ctx: Ctx):
    from .api_chat import sees

    return ok(sees(vault, ctx.params["model"]))


def _get_chat(vault: Vault, ctx: Ctx):
    return ok(CH.load_chat(vault, ctx.params["id"]))


def _get_vpn(vault: Vault, ctx: Ctx):
    from . import vpnkey

    return ok(vpnkey.status(vault))


def _get_connect(vault: Vault, ctx: Ctx):
    from . import cli

    return ok(cli.connected())


def _get_chat_poll(vault: Vault, ctx: Ctx):
    return ok(CH.state(ctx.params["id"]))


def _get_ach(vault: Vault, ctx: Ctx):
    from . import achievements

    return ok(achievements.summary(vault))


def _get_prompts(vault: Vault, ctx: Ctx):
    from .chat import prompts as PRM

    return ok({"prompts": PRM.all_prompts(vault), **PRM.settings(vault)})


def _get_plan_models(vault: Vault, ctx: Ctx):
    from .chat import planner as PL

    return ok({"models": PL.models_table(vault)})


def _get_models(vault: Vault, ctx: Ctx):
    PR.find_strata(vault)  # раз за запуск: уже запущенная на этом компьютере Strata видна сама
    return ok({"providers": PR.status(vault), "default_model": CH.default_model(vault)})


def _get_agent(vault: Vault, ctx: Ctx):
    prof = P.load(vault)
    return ok(
        {
            "catalog": P.catalog_view(prof),
            "presets": {k: {"name": v["name"], "note": v["note"]} for k, v in P.PRESETS.items()},
            "simple": P.SIMPLE,
            "profile": prof,
            "proxy_system": net.system_proxy(),
            "proxy_used": net.describe(),
            "proxy_password_set": bool(net.stored_password(vault)),
            "brave_set": bool(_web().brave_key()),
        }
    )


def _get_agent_pack(vault: Vault, ctx: Ctx):
    return ok(P.export_pack(P.load(vault), ctx.params["name"]))


def _get_learn_live(vault: Vault, ctx: Ctx):
    return ok({"events": LE.live(vault, ctx.params["since"])})


def _get_local(vault: Vault, ctx: Ctx):
    from . import localllm

    if ctx.params["probe"]:
        localllm.probe_speed()
    return ok({**localllm.status(), "offer": P.load(vault).get("local_offer", "")})


def _get_sync(vault: Vault, ctx: Ctx):
    from . import sync

    return ok(sync.public(vault))


def _get_local_heat(vault: Vault, ctx: Ctx):
    from . import heat

    return ok(heat.status())


def _get_net_detect(vault: Vault, ctx: Ctx):
    from . import vpn_detect

    return ok(vpn_detect.detect())


def _get_efs(vault: Vault, ctx: Ctx):
    from . import efs

    return ok(efs.status(vault))


def _get_crypto(vault: Vault, ctx: Ctx):
    from . import crypt

    return ok(crypt.status(vault.root))


def _get_crypto_key(vault: Vault, ctx: Ctx):
    from . import crypt

    return ok({"key": crypt.key_b64(vault.root)})


def _get_scribe_settings(vault: Vault, ctx: Ctx):
    from .api_chat import scribe_settings

    return ok(scribe_settings(vault))


def _get_scribe_status(vault: Vault, ctx: Ctx):
    from . import scribe

    return ok(scribe.status(vault))


def _get_memory_status(vault: Vault, ctx: Ctx):
    from .api_chat import memory_status

    return ok(memory_status(vault))


def _get_outgoing(vault: Vault, ctx: Ctx):
    from . import outgoing as OG

    p = ctx.params
    return ok({**OG.report(vault, max(1, min(90, p["days"]))), "redact": bool(P.load(vault).get("redact", True))})


def _get_telegram(vault: Vault, ctx: Ctx):
    from .learn import tg_api

    return ok(tg_api.status(vault))


def _get_quiz(vault: Vault, ctx: Ctx):
    from . import play

    return ok(play.quiz(vault))


def _get_interview(vault: Vault, ctx: Ctx):
    from . import play

    return ok({"questions": [{"key": k, "q": q, "eg": eg} for k, q, eg in play.INTERVIEW]})


def _get_telegram_chats(vault: Vault, ctx: Ctx):
    from .learn import tg_api

    return ok({"chats": tg_api.dialogs(vault)})


def _get_obsidian(vault: Vault, ctx: Ctx):
    from pathlib import Path

    from . import extra

    mine = extra.folders(P.load(vault))
    return ok(
        {
            "vaults": [{**v, "added": v["path"] in mine} for v in extra.obsidian_vaults(vault)],
            "folders": [{"path": p, "obsidian": extra.is_obsidian(Path(p))} for p in mine],
        }
    )


def _get_engine(vault: Vault, ctx: Ctx):
    from . import tuning

    return ok(
        {**tuning.get(vault), "usage": tuning.month_usage(vault), "presets": tuning.PRESETS, "limits": tuning.LIMITS}
    )


def _get_learn_brain(vault: Vault, ctx: Ctx):
    from .api_chat import brain_status

    return ok(brain_status(vault))


def _get_memory_why(vault: Vault, ctx: Ctx):
    from .api_chat import why

    return ok(why(vault, ctx.params["text"]))


def _get_context(vault: Vault, ctx: Ctx):
    p = ctx.params
    if not P.memory_on(vault):
        return ok({"text": "", "parts": 0, "off": True})
    text, total = context_for(vault, p["client"], part=p["part"])
    return ok({"text": text, "parts": total})


def _get_now(vault: Vault, ctx: Ctx):
    return ok({"text": generate_now(vault)})


def _get_notes(vault: Vault, ctx: Ctx):
    p = ctx.params
    notes = [n for n in vault.notes() if not p["scope"] or n.scope == p["scope"]]
    return ok(
        [
            {
                "rel": n.rel,
                "title": n.title,
                "scope": n.scope,
                "status": n.meta.get("status", ""),
                "goal": n.meta.get("goal", ""),
                "updated": n.meta.get("updated", ""),
            }
            for n in notes
        ]
    )


def _get_note(vault: Vault, ctx: Ctx):
    rel = ctx.params["rel"]
    if not EDITABLE.match(rel):
        return err(400, "этот файл нельзя открыть")
    raw = vault.read_raw(rel) or ""
    from .journal import _hash

    return ok({"rel": rel, "raw": raw, "hash": _hash(raw)})


def _get_journal(vault: Vault, ctx: Ctx):
    return ok(events(vault, ctx.params["limit"]))


def _get_stale(vault: Vault, ctx: Ctx):
    return ok([{"rel": s.rel, "text": s.text, "age": s.age_days, "date": s.date.isoformat()} for s in vault.stale()])


def _get_clients(vault: Vault, ctx: Ctx):
    return ok([c.__dict__ for c in load_clients(vault).values()])


def _get_learn_status(vault: Vault, ctx: Ctx):
    from .api_learn import _state

    s = S.load(vault)
    st = _state(vault)
    return ok(
        {
            "memory_on": P.memory_on(vault),
            "settings": S.public(s),
            "sources": S.SOURCES,
            "brains": S.BRAINS,
            "modes": S.MODES_RU,
            "status": LE.status(vault),
            "progress": {"running": st["running"], "log": st["log"][-8:], "last": st["last"]},
        }
    )


def _get_learn_items(vault: Vault, ctx: Ctx):
    from .api_learn import _item
    from .learn.ledger import Ledger

    p = ctx.params
    led = Ledger(vault)
    view = p["view"]
    if view == "queue":
        items = led.queue()
    elif view == "learned":
        items = sorted(
            (i for i in led.items if i["state"] in ("written", "confirmed")), key=lambda i: i["last_seen"], reverse=True
        )
    elif view == "observed":
        items = sorted(
            (i for i in led.items if i["state"] in ("observed", "weak")), key=lambda i: i["last_seen"], reverse=True
        )
    else:
        items = sorted(
            (i for i in led.items if i["state"] in ("rejected", "forgotten")),
            key=lambda i: i["last_seen"],
            reverse=True,
        )
    counts = led.counts()
    out = [_item(i) for i in items[: p["limit"]]]
    if view == "queue":  # статусы старше месяца: переспрашиваются, а не подаются молча как текущие
        from .memory import stale_items

        stale = stale_items(vault)
        counts["stale"] = len(stale)
        out += stale[: p["limit"]]
    return ok({"items": out, "counts": counts})


# -- POST-обработчики --------------------------------------------------------


def _post_remember(vault: Vault, ctx: Ctx):
    p = ctx.params
    if not P.memory_on(vault):
        return 409, {"error": P.MEMORY_OFF, "off": True}
    ev = remember(vault, p["fact"], p["where"], p["client"])
    return ok({"id": ev["id"], "path": ev["paths"][0]})


def _post_undo(vault: Vault, ctx: Ctx):
    from .api_learn import on_undo

    p = ctx.params
    ev = undo(vault, p["id"])
    on_undo(vault, p["id"])
    return ok({"ok": True, "summary": ev["summary"]})


def _get_saves(vault: Vault, ctx: Ctx):
    from .memory import list_saves

    return ok({"saves": list_saves(vault)})


def _post_saves_restore(vault: Vault, ctx: Ctx):
    from .memory import restore_save

    try:
        return ok(restore_save(vault, ctx.params["path"]))
    except ValueError as e:
        return err(400, str(e))


def _post_memory_export(vault: Vault, ctx: Ctx):
    """BP-16: the memory exported as open Markdown files (a folder); forbidden while encryption is on."""
    import shutil
    from pathlib import Path

    from . import crypt
    from .vault import GENERATED, SAVES, SYSTEM

    dest_raw = str(ctx.params.get("path") or "").strip()
    if not dest_raw:
        return err(400, "укажи папку для экспорта")
    dest = Path(dest_raw).expanduser()
    if crypt.enabled(vault.root):
        return err(403, "Память зашифрована — экспорт открытыми Markdown-файлами запрещён. Сначала сними шифрование.")
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in sorted(vault.root.rglob("*.md")):
        rel = f.relative_to(vault.root).as_posix()
        if f.is_relative_to(vault.service):  # .mnema: chats, journal snapshots and service files are not the memory
            continue
        if rel in GENERATED or rel.startswith((SAVES + "/", SYSTEM + "/")):
            continue
        tgt = dest / rel
        tgt.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, tgt)
        n += 1
    return ok({"ok": True, "path": str(dest), "files": n})


def _post_note(vault: Vault, ctx: Ctx):
    p = ctx.params
    rel, raw = p["rel"], p["raw"]
    if not EDITABLE.match(rel) or not isinstance(raw, str):
        return err(400, "этот файл нельзя править")
    from .journal import _hash

    with vault.lock():
        if p["base"] and _hash(vault.read_raw(rel) or "") != p["base"]:
            return err(
                409,
                "Файл изменился, пока ты его правил: Mnemai дописала в него новое. Открой его заново и повтори правку.",
            )
        ev = write_with_journal(vault, "owner", rel, raw, f"правка вручную: {rel}")
    generate_now(vault)
    return ok({"id": ev["id"]})


def _post_clients(vault: Vault, ctx: Ctx):
    items = ctx.body if isinstance(ctx.body, list) else ctx.body.get("clients", [])
    clients = {}
    for it in items:
        known = {k: v for k, v in it.items() if k in Client.__dataclass_fields__}
        c = Client(**known)
        clients[c.id] = c
    if not clients:
        return err(400, "пустой список")
    save_clients(vault, clients)
    return ok({"ok": True})


def _post_chat_send(vault: Vault, ctx: Ctx):
    p = ctx.params
    return ok(
        CH.send(
            vault,
            p["text"],
            p["chat"],
            p["model"],
            files=p["files"] or None,
            quote=p["quote"],
            web=p["web"],
            consortium=p["consortium"] or None,
            terms=p["terms"],
            opener=p["opener"],
            private=p["private"],
        )
    )


def _post_plan_budget(vault: Vault, ctx: Ctx):
    from .chat import planner as PL

    task = ctx.params["task"].strip()
    if not task:
        return ok({"usd": 0.05, "cheap_usd": 0.0, "note": "пустая задача — запасной бюджет"})
    return ok(PL.recommend_budget(vault, task))


def _post_plan_propose(vault: Vault, ctx: Ctx):
    from .chat import planner as PL

    p = ctx.params
    budget = p["budget"]
    if budget is not None:
        try:
            budget = float(budget)
        except (TypeError, ValueError):
            budget = None
    return ok(
        {
            "plans": PL.propose(
                vault,
                p["task"].strip(),
                p["chat"] or "",
                p["planner"] or "auto",
                budget=budget,
                economy=p["economy"],
            )
        }
    )


def _post_plan_run(vault: Vault, ctx: Ctx):
    from .chat import planner as PL

    p = ctx.params
    plan = p["plan"] or {}
    if not isinstance(plan, dict):
        raise ValueError("плохой план")
    cid = p["chat"] or ""
    if not cid:
        task = " ".join(str(plan.get("task") or "План").split())[:60]
        chat = {
            "id": CH.secrets.token_hex(6),
            "title": task or "План",
            "created": CH._now(),
            "session": CH.current_session(vault)["id"],
            "messages": [],
        }
        CH.save_chat(vault, chat)
        cid = chat["id"]
    return ok(PL.run(vault, cid, plan))


def _post_chat_redo(vault: Vault, ctx: Ctx):
    p = ctx.params
    return ok(CH.redo(vault, p["chat"], p["web"]))


def _post_chat_useful(vault: Vault, ctx: Ctx):
    p = ctx.params
    return ok(CH.mark_useful(vault, p["chat"], p["index"], p["on"]))


def _post_portrait_refresh(vault: Vault, ctx: Ctx):
    from . import portrait

    r = portrait.refresh(vault, force=ctx.params["force"])
    if r["written"]:
        generate_now(vault)
    return ok(r)


def _post_session_new(vault: Vault, ctx: Ctx):
    return ok(CH.new_session(vault))


def _post_session_rename(vault: Vault, ctx: Ctx):
    p = ctx.params
    return ok({"names": CH.rename_session(vault, p["id"], p["name"])})


def _post_session_delete(vault: Vault, ctx: Ctx):
    return ok({"deleted": CH.delete_session(vault, ctx.params["id"])})


def _post_chat_learn_now(vault: Vault, ctx: Ctx):
    return ok(CH.learn_chat_now(vault, ctx.params["id"]))


def _post_chat_update(vault: Vault, ctx: Ctx):
    p = ctx.params
    return ok(
        CH.update_chat(
            vault,
            p["id"],
            p["title"],
            p["pinned"],
            p["private"],
            p["consortium"],
        )
    )


def _post_chat_regenerate(vault: Vault, ctx: Ctx):
    p = ctx.params
    return ok(CH.regenerate(vault, p["chat"], p["model"]))


def _post_chat_cons(vault: Vault, ctx: Ctx):
    from .chat import consortium as CO

    p, b = ctx.params, ctx.body
    return ok(
        CO.control(
            vault,
            p["chat"],
            p["action"],
            p["members"],
            int(p["rounds"]) if p["rounds"] else None,
            p["model"],
            {k: b.get(k) for k in ("format", "roles", "summarizer", "length", "search", "challenge")},
        )
    )


def _post_vpn(vault: Vault, ctx: Ctx):
    from . import vpnkey

    p = ctx.params
    a = p["action"]
    if a == "connect":
        return ok({**vpnkey.connect(vault, p["key"], p["service"]), **vpnkey.status(vault)})
    if a == "off":
        return ok(vpnkey.disconnect(vault))
    raise ValueError("неизвестное действие")


def _post_web_page(vault: Vault, ctx: Ctx):
    from . import web

    url = ctx.params["url"].strip()
    if not url.startswith(("http://", "https://")):
        raise ValueError("нужна ссылка, начинающаяся с http")
    try:
        d = web.fetch(url)
    except Exception as e:
        raise ValueError(f"не открылась страница: {str(e)[:160]}")
    if not (d.get("text") or "").strip():
        raise ValueError("на странице нет текста, который можно прочитать")
    return ok({"url": d["url"], "title": d.get("title") or url, "text": d["text"][:120_000]})


def _post_chat_action(vault: Vault, ctx: Ctx):
    p = ctx.params
    return ok(CH.answer_action(p["chat"], p["id"], p["choice"]))


def _post_chat_sudo(vault: Vault, ctx: Ctx):
    p = ctx.params
    return ok(CH.answer_sudo(p["chat"], p["id"], p["password"], p["choice"]))


def _post_files(vault: Vault, ctx: Ctx):
    from pathlib import Path

    from . import osapi
    from .chat import tools as TL

    raw = ctx.params["path"].strip()
    try:
        fpath = Path(raw).expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        return err(400, "Не поняла путь к файлу")
    if not fpath.exists():
        return err(404, "Файла нет: его переместили или удалили")
    if ctx.path == "/api/files/open":
        if not fpath.is_file():
            return err(404, "Файла нет: его переместили или удалили")
        if fpath.suffix.lower() not in TL.OPENABLE:
            return err(400, "Такой файл открывается только из папки: «Показать в папке»")
        osapi.open_path(fpath)
    else:
        osapi.reveal(fpath) if fpath.is_file() else osapi.open_path(fpath)
    return ok({"ok": True})


def _post_chat_stop(vault: Vault, ctx: Ctx):
    CH.stop(ctx.params["chat"])
    return ok({"ok": True})


def _post_chat_delete(vault: Vault, ctx: Ctx):
    from .memory import move_chat_files_to_saves

    move_chat_files_to_saves(vault, ctx.params["id"])  # BP-16: the chat's attachments stay in «95 Saves»
    CH.delete_chat(vault, ctx.params["id"])
    return ok({"ok": True})


def _post_providers(vault: Vault, ctx: Ctx):
    p = ctx.params
    PR.save(vault, p["id"], endpoint=p["endpoint"], key=p["key"], disabled=p["disabled"], folder=p["folder"])
    return ok({"providers": PR.status(vault)})


def _post_providers_claude_login(vault: Vault, ctx: Ctx):
    return ok(PR.claude_login())


def _post_providers_codex_login(vault: Vault, ctx: Ctx):
    return ok(PR.codex_login(vault))


def _post_providers_check(vault: Vault, ctx: Ctx):
    r = PR.check(vault, ctx.params["id"])
    return ok({**r, "providers": PR.status(vault)})


def _post_providers_models(vault: Vault, ctx: Ctx):
    p = ctx.params
    try:
        ids = PR.fetch_models(vault, p["id"])
    except Exception as e:
        from . import errors as E

        msg = E.human(e, E.provider_name(p["id"]), vpn=E.vpn_name(vault))
        if E.account_problem(e):  # отклонённый ключ — это не «подключено»
            PR.note_problem(vault, p["id"], msg)
        return ok({"ok": False, "error": msg, "providers": PR.status(vault)})
    return ok({"ok": True, "models": ids, "providers": PR.status(vault)})


def _post_telegram(vault: Vault, ctx: Ctx):
    from .learn import tg_api

    return ok(tg_api.configure(vault, ctx.body))


def _post_compare(vault: Vault, ctx: Ctx):
    from . import play

    p = ctx.params
    return ok(play.compare(vault, p["question"] or "", p["models"]))


def _post_quiz(vault: Vault, ctx: Ctx):
    from . import play

    p = ctx.params
    return ok(play.quiz_answer(vault, p["id"], p["verdict"], p["text"]))


def _post_interview(vault: Vault, ctx: Ctx):
    from . import play

    return ok(play.interview_save(vault, ctx.params["answers"] or {}))


def _post_share_save(vault: Vault, ctx: Ctx):
    import base64
    import re as _re
    import time as _time
    from pathlib import Path as _P

    from . import osapi

    p = ctx.params
    data = base64.b64decode((p["png"] or "").split(",", 1)[-1])
    if not data.startswith(b"\x89PNG"):
        raise ValueError("это не картинка")
    folder = _P.home() / "Pictures" / "Mnemai"
    folder.mkdir(parents=True, exist_ok=True)
    name = _re.sub(r"[^\w -]+", "", p["name"] or "mnemai")[:40].strip() or "mnemai"
    fpath = folder / f"{name} {_time.strftime('%Y-%m-%d %H-%M-%S')}.png"
    fpath.write_bytes(data)
    osapi.reveal(fpath)
    return ok({"ok": True, "path": str(fpath)})


def _post_settings_reset(vault: Vault, ctx: Ctx):
    from . import tuning

    tuning.save(vault, {"mode": "balance", "month": 0})
    d = P.DEFAULT
    P.save(
        vault,
        {k: d[k] for k in ("economy", "scribe_mode", "scribe_model", "scribe_keep_audio", "tools", "tools_ask")},
    )
    return ok({"ok": True})


def _post_agent(vault: Vault, ctx: Ctx):
    b = ctx.body
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
            "pc_access",
            "tool_folders",
            "tools_ask",
            "memory_on",
            "memory_asked",
        )
    }
    for k in ("default_model", "last_model", "scribe_model", "scribe_summary_model"):
        if "[object" in str(patch.get(k) or ""):  # битая отдача со страницы никогда не запоминается
            patch.pop(k)
    prof = P.save(vault, patch) if patch else P.load(vault)
    if "extra_folders" in patch:  # только что добавленная папка читается в фоне
        from . import extra

        extra.warm_all(vault)
    if "proxy" in b:  # адрес — в профиле, пароль — в системном хранилище Windows
        net.save(vault, str(b.get("proxy") or ""), b.get("proxy_password") if "proxy_password" in b else None)
        prof = P.load(vault)
    if "brave_key" in b:  # необязательный ключ поиска: хранится вне памяти, как ключи ИИ
        from . import web
        from .learn import secrets_store
        from .learn.settings import _vid

        secrets_store.put(_vid(vault), "web.brave", str(b["brave_key"] or "").strip())
        web.set_brave_key(str(b["brave_key"] or ""))
    auto = (b.get("simple") or {}).get("autonomy")
    if auto in S.MODES:  # один движок задаёт, как учится каждый источник
        s = S.load(vault)
        if not s.get("demo"):
            for sid, src in s["sources"].items():
                src["mode"] = auto if sid != "browser_history" or auto == "observe" else src["mode"]
            S.save(vault, s)
    return ok({"profile": prof, "catalog": P.catalog_view(prof)})


def _post_net_check(vault: Vault, ctx: Ctx):
    p = ctx.params
    pw = p["password"]
    return ok(net.check(p["proxy"], net.stored_password(vault) if pw is None else str(pw)))


def _post_local(vault: Vault, ctx: Ctx):
    from . import localllm

    b = ctx.body
    what = ctx.path.rsplit("/", 1)[-1]
    if what == "download":
        return ok(localllm.start_download(str(b.get("id", ""))))
    if what == "pause":
        return ok(localllm.pause_download())
    if what == "cancel":
        return ok(localllm.cancel_download())
    if what == "delete":
        localllm.delete_model(str(b.get("id", "")))
        return ok({"ok": True})
    if what == "probe":
        return ok(localllm.probe_speed(force=True))
    if what == "warm":
        from .chat import small

        mid = str(b.get("model", "")).partition(":")[2] or str(b.get("model", ""))
        return ok(small.warm(vault, mid) if small.is_small("local", mid) else {"ready": True, "skipped": True})
    if what == "cool":
        from . import heat

        return ok(heat.cool_down(vault))
    if what == "stop":
        from . import heat

        return ok(heat.stop_model())
    if what == "add_file":
        return ok(localllm.add_custom_file(str(b.get("path", ""))))
    if what == "add_url":
        m = localllm.add_custom_url(str(b.get("url", "")))
        return ok(localllm.start_download(m["id"]))
    if what == "offer":
        if b.get("claim"):  # приветствие показывается один раз, сколько бы страница ни загружалась
            with _OFFER_LOCK:
                if P.load(vault).get("local_offer"):
                    return ok({"claimed": False})
                P.save(vault, {"local_offer": "shown"})
            return ok({"claimed": True})
        P.save(vault, {"local_offer": str(b.get("state", "dismissed"))})
        return ok({"ok": True})
    return None


def _post_ach_seen(vault: Vault, ctx: Ctx):
    from . import achievements

    achievements.seen(vault)
    return ok({"ok": True})


def _post_ach_event(vault: Vault, ctx: Ctx):
    return ok({"ok": True})  # учитывается в achievements.on_post


def _post_engine(vault: Vault, ctx: Ctx):
    from . import tuning

    return ok({**tuning.save(vault, ctx.body), "usage": tuning.month_usage(vault)})


def _post_crypto(vault: Vault, ctx: Ctx):
    from .api_chat import crypto_post

    b = ctx.body or {}
    if str(b.get("action", "")) == "recover":  # BP-15: a forgotten password is restored by the recovery key only
        from . import crypt

        try:
            r = crypt.recover(vault.root, str(b.get("recovery", "")), str(b.get("password", "")))
        except crypt.BadPassword:
            return err(403, "Ключ восстановления не подходит")
        except ValueError as e:
            return err(400, str(e))
        return ok({**crypt.status(vault.root), **r})
    return crypto_post(vault, ctx.body)


def _post_efs(vault: Vault, ctx: Ctx):
    from . import efs

    what = ctx.params["action"]
    if what == "on":
        return ok(efs.enable(vault))
    if what == "off":
        return ok(efs.disable(vault))
    if what == "backup":
        return ok({**efs.status(vault), "file": efs.backup_key()})
    return ok(efs.status(vault))


def _post_sync(vault: Vault, ctx: Ctx):
    from . import sync

    b = ctx.body
    what = ctx.path.rsplit("/", 1)[-1]
    if what == "add":
        sync.add(vault, str(b.get("kind", "")), str(b.get("path", "")), str(b.get("url", "")), str(b.get("token", "")))
    elif what == "remove":
        sync.remove(vault, str(b.get("id", "")))
    elif what == "minutes":
        sync.set_minutes(vault, int(b.get("minutes") or 10))
    elif what == "now":
        return ok({**sync.public(vault), "result": sync.run(vault, str(b.get("id", "")))})
    return ok(sync.public(vault))


def _post_chat_self_ask(vault: Vault, ctx: Ctx):
    p = ctx.params
    return ok(CH.answer_self_ask(vault, p["chat"], p["i"], p["action"], p["text"]))


def _post_prompts_answer(vault: Vault, ctx: Ctx):
    p = ctx.params
    return ok(CH.answer_offer(vault, p["chat"], p["choice"]))


def _post_prompts_delete(vault: Vault, ctx: Ctx):
    from .chat import prompts as PRM

    PRM.delete(vault, ctx.params["file"])
    return ok({"prompts": PRM.all_prompts(vault)})


def _post_prompts_open(vault: Vault, ctx: Ctx):
    import os

    from . import osapi
    from .chat import prompts as PRM

    f = PRM.folder(vault) / os.path.basename(ctx.params["file"])
    osapi.open_path(f if f.exists() else PRM.folder(vault))
    return ok({"ok": True})


def _post_voice(vault: Vault, ctx: Ctx):
    from . import voice

    b = ctx.body
    what = ctx.path.rsplit("/", 1)[-1]
    if what == "start":
        return ok(voice.start(vault))
    if what == "stop":
        return ok(voice.stop(vault, str(b.get("lang", ""))))
    return ok(voice.cancel())


def _post_scribe(vault: Vault, ctx: Ctx):
    from . import scribe

    b = ctx.body
    what = ctx.path.rsplit("/", 1)[-1]
    if what == "start":
        return ok(scribe.start(vault, str(b.get("name", ""))))
    if what == "stop":
        return ok(scribe.stop(vault, str(b.get("model", ""))))
    if what == "import":
        return ok(
            scribe.import_file(
                vault,
                str(b.get("filename", "")),
                str(b.get("data", "")),
                str(b.get("name", "")),
                str(b.get("model", "")),
            )
        )
    if what == "reset":
        scribe.st(vault).update(status="idle")
        return ok(scribe.status(vault))
    if what == "answer":  # облако или этот компьютер — спрашивается, когда компьютер медленный
        s = scribe.st(vault)
        choice = "cloud" if b.get("choice") == "cloud" else "local"
        if b.get("remember"):
            P.save(vault, {"scribe_mode": "fast" if choice == "cloud" else "private"})
        s["choice"] = choice
        if s.get("_answer"):
            s["_answer"].set()
        return ok(scribe.status(vault))
    if what == "settings":
        from . import scribe_cloud as SC
        from .api_chat import scribe_settings
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
        return ok(scribe_settings(vault))
    return None


def _post_import_chatgpt(vault: Vault, ctx: Ctx):
    import base64

    p = ctx.params
    raw = base64.b64decode((p["data"] or "").split(",")[-1])
    name = p["filename"]
    dest = vault.service / "imports"
    dest.mkdir(parents=True, exist_ok=True)
    if name.lower().endswith(".zip"):  # весь архив выгрузки ChatGPT
        import io
        import zipfile

        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            member = next((n for n in z.namelist() if n.endswith("conversations.json")), None)
            if not member:
                return err(400, "в архиве нет conversations.json")
            raw = z.read(member)
    import json as _json

    try:
        convs = _json.loads(raw.decode("utf-8"))
    except ValueError:
        return err(400, "это не выгрузка ChatGPT")
    (dest / "conversations.json").write_bytes(raw)
    s = S.load(vault)
    if s.get("demo"):
        return err(403, "в демо обучение выключено")
    s["sources"]["chatgpt_export"].update(
        enabled=True,
        options={**s["sources"]["chatgpt_export"]["options"], "path": str(dest / "conversations.json")},
    )
    S.save(vault, s)
    from .api_learn import start_run

    start_run(vault, initial=True, only=["chatgpt_export"])
    return ok({"ok": True, "conversations": len(convs) if isinstance(convs, list) else 0})


def _post_open_url(vault: Vault, ctx: Ctx):
    import webbrowser

    url = ctx.params["url"]
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
        return err(400, "этот адрес не открываю")
    webbrowser.open(url)  # обычный браузер владельца
    return ok({"ok": True})


def _post_memory_open(vault: Vault, ctx: Ctx):
    from . import osapi

    osapi.open_path(vault.root)  # проводник/файловый менеджер на папке памяти
    return ok({"ok": True, "folder": str(vault.root)})


def _post_connect(vault: Vault, ctx: Ctx):
    from . import cli

    target = ctx.params["target"]
    if target not in ("claude-code", "claude-desktop", "cursor"):
        return err(400, "неизвестная цель")
    said, orig = [], cli.out
    cli.out = said.append  # у оконного приложения нет консоли
    try:
        cli.install(target, vault, True, None)
    except SystemExit as e:
        return ok({"ok": False, "message": str(e)})
    except Exception as e:
        return ok({"ok": False, "message": str(e)[:300]})
    finally:
        cli.out = orig
    return ok({"ok": True, "message": "\n".join(said)[-400:]})


def _post_agent_pack(vault: Vault, ctx: Ctx):
    prof = P.import_pack(vault, ctx.body)
    return ok({"profile": prof, "catalog": P.catalog_view(prof)})


def _post_learn_settings(vault: Vault, ctx: Ctx):
    cur = S.load(vault)
    if cur.get("demo"):
        return err(403, "В демо обучение выключено: заведи свою память")
    s = S.save(vault, S.merge_from_ui(cur, {k: v for k, v in ctx.body.items() if k != "demo"}))
    return ok({"settings": S.public(s)})


def _post_learn_run(vault: Vault, ctx: Ctx):
    from .api_learn import start_run

    p = ctx.params
    return ok(start_run(vault, p["initial"], p["only"]))


def _post_learn_review(vault: Vault, ctx: Ctx):
    from .api_learn import _item
    from .chat import engine as CH

    p = ctx.params
    if p["id"].startswith("stale:"):
        from .memory import resolve_stale

        ev = resolve_stale(vault, p["id"], p["action"], p["text"])
        return ok({"item": {"id": p["id"], "state": "resolved", "event": ev.get("id", "")}})
    if p["action"] == "keep_all":
        # «Запомнить всё»: этот факт и все остальные ждущие вопросы памяти — один ответ за все
        if p["chat"]:

            def clear_asks(c):
                c["learn_asks"] = []
                c.pop("learn_ask", None)

            try:
                CH.modify_chat(vault, str(p["chat"]), clear_asks)
            except KeyError:
                pass
        if p["id"]:
            try:
                LE.review(vault, p["id"], "keep")
            except KeyError:
                pass
        return ok({"done": LE.review_all(vault, "keep")})
    if p["chat"]:  # ответ под разговором: вопрос уходит, показывается следующий из очереди

        def drop_ask(c):
            qs = [q for q in (c.get("learn_asks") or []) if q.get("item") != p["id"]]
            if (
                c.get("learn_ask")
                and c["learn_ask"].get("item") != p["id"]
                and all(q.get("item") != c["learn_ask"].get("item") for q in qs)
            ):
                qs.insert(0, c["learn_ask"])
            c["learn_asks"] = qs
            if qs:
                c["learn_ask"] = qs[0]
            else:
                c.pop("learn_ask", None)

        try:
            CH.modify_chat(vault, str(p["chat"]), drop_ask)
        except KeyError:
            pass
    it = LE.review(vault, p["id"], p["action"], p["text"], p["where"])
    return ok({"item": _item(it)})


def _post_learn_review_all(vault: Vault, ctx: Ctx):
    p = ctx.params
    return ok({"done": LE.review_all(vault, p["action"], p["state"])})


def _post_learn_test_brain(vault: Vault, ctx: Ctx):
    from .learn.brains import make_brain
    from .learn.sources import Episode

    b = ctx.body
    s = S.merge_from_ui(S.load(vault), b) if b else S.load(vault)
    try:
        brain = make_brain(s)
        brain.vault = vault
    except Exception as e:  # ещё не заполнено: скажи, чего не хватает, а не падай
        return ok({"ok": False, "error": str(e)[:300]})
    sample = [Episode("test", "t1", "", "Запомни, что я пью кофе без сахара. Решил начать пилот в понедельник.")]
    try:
        got = brain.extract(sample, "")
    except Exception as e:
        return ok({"ok": False, "error": str(e)[:300]})
    return ok({"ok": bool(got), "found": [g["text"] for g in got]})


# -- /api/ping и /api/app/*: самопроверка и маршруты-адаптеры окна -----------------


def _get_ping(vault: Vault, ctx: Ctx):
    return ok({"ok": True, "version": __version__, "lang": P.load(vault).get("lang") or "en"})


def _get_app_selftest(vault: Vault, ctx: Ctx):
    from . import crypt, ocr

    from .learn import tg_api

    return ok({"ocr": ocr.selftest(), "crypt": crypt.selftest(), "telegram": tg_api.selftest()})


def _get_app_named(vault: Vault, ctx: Ctx):
    """GET /api/app/<name>: хуки окна (show, info, switch, quit, vaults, update); без окна — порт и «не desktop»."""
    name = ctx.path.rsplit("/", 1)[-1]
    hook = APP_HOOKS.get(name)
    return ok(hook() if hook else {"desktop": False, "port": APP_PORT})


def _get_app_fallback(vault: Vault, ctx: Ctx):
    return ok({"desktop": False, "port": APP_PORT})


def _post_app_named(vault: Vault, ctx: Ctx):
    """POST /api/app/<name>: хуки окна (autostart, close_pref, vault_open, …); без окна — «не desktop»."""
    name = ctx.path.rsplit("/", 1)[-1]
    hook = APP_HOOKS.get(name)
    return ok(hook(ctx.body) if hook else {"desktop": False})


def _post_app_fallback(vault: Vault, ctx: Ctx):
    return ok({"desktop": False})


def _get_app_default_path(vault: Vault, ctx: Ctx):
    """Папка по умолчанию для новой памяти — та же функция приложения, что и слот js_api default_path."""
    from .firstrun import default_path

    return ok({"path": default_path()})


def _post_app_create(vault: Vault, ctx: Ctx):
    """Создать память (первый запуск): та же функция приложения, что и слот js_api create."""
    from .firstrun import create

    b = ctx.body
    failure, v = create(
        str(b.get("path") or ""), str(b.get("proxy") or ""), str(b.get("password") or ""), b.get("prefs")
    )
    if failure:
        return err(failure[1], failure[0])  # единая обёртка ошибок: 400 — невалидный путь, 500 — сбой
    hook = APP_HOOKS.get("open_vault")
    if hook:
        hook(v, False, 2.4)  # с окном — переключение на новую память, как в визарде
    return ok({"ok": True, "path": str(v.root)})


def _post_app_demo(vault: Vault, ctx: Ctx):
    """Демо-память: та же функция приложения, что и слот js_api demo."""
    from .firstrun import demo

    b = ctx.body
    failure, v = demo(str(b.get("proxy") or ""), str(b.get("password") or ""), b.get("prefs"))
    if failure:
        return err(failure[1], failure[0])
    hook = APP_HOOKS.get("open_vault")
    if hook:
        hook(v, True, 0.3)
    return ok({"ok": True, "path": str(v.root)})


def _post_app_open_existing(vault: Vault, ctx: Ctx):
    """«Указать, где она»: та же функция приложения, что и слот js_api open_existing."""
    from .firstrun import open_existing

    b = ctx.body
    failure, v = open_existing(str(b.get("path") or ""), str(b.get("lang") or "ru"))
    if failure:
        return err(failure[1], failure[0])
    hook = APP_HOOKS.get("open_vault")
    if hook:
        hook(v, False, 0.4)
    return ok({"ok": True, "path": str(v.root)})


# -- таблица маршрутов --------------------------------------------------------

GET_ROUTES: tuple[Route, ...] = (
    Route("GET", "/api/ping", _get_ping, RequestSchema(), ResponseSchema("object", ("ok", "version", "lang"))),
    Route(
        "GET",
        "/api/app/selftest",
        _get_app_selftest,
        RequestSchema(),
        ResponseSchema("object", ("ocr", "crypt", "telegram")),
    ),
    Route("GET", "/api/app/show", _get_app_named, RequestSchema(), ResponseSchema("object", ("ok",))),
    Route(
        "GET",
        "/api/app/info",
        _get_app_named,
        RequestSchema(),
        ResponseSchema("object", ("version", "port", "vault", "demo", "autostart", "desktop", "on_close")),
    ),
    Route("GET", "/api/app/switch", _get_app_named, RequestSchema(), ResponseSchema("object", ("ok",))),
    Route("GET", "/api/app/quit", _get_app_named, RequestSchema(), ResponseSchema("object", ("ok",))),
    Route("GET", "/api/app/vaults", _get_app_named, RequestSchema(), ResponseSchema("object", ("current", "list"))),
    Route(
        "GET",
        "/api/app/update",
        _get_app_named,
        RequestSchema(),
        ResponseSchema("object", ("desktop", "current", "available")),
    ),
    Route(
        "GET",
        "/api/app/",
        _get_app_fallback,
        RequestSchema(),
        ResponseSchema("object", ("desktop", "port")),
        prefix=True,
    ),
    Route("GET", "/api/app/default_path", _get_app_default_path, RequestSchema(), ResponseSchema("object", ("path",))),
    Route("GET", "/api/chats", _get_chats, RequestSchema(query=fields(q=("str", ""), sort=("str", "date")))),
    Route(
        "GET",
        "/api/knowledge",
        _get_knowledge,
        RequestSchema(),
        response_schema=ResponseSchema("object", ("sections",)),
    ),
    Route("GET", "/api/chat/export", _get_chat_export, RequestSchema(query=fields(id=("str", "")))),
    Route("GET", "/api/chat/sees", _get_chat_sees, RequestSchema(query=fields(model=("str", "")))),
    Route("GET", "/api/chat", _get_chat, RequestSchema(query=fields(id=("str", "")))),
    Route("GET", "/api/vpn", _get_vpn, RequestSchema()),
    Route("GET", "/api/connect", _get_connect, RequestSchema()),
    Route("GET", "/api/chat/poll", _get_chat_poll, RequestSchema(query=fields(id=("str", "")))),
    Route("GET", "/api/ach", _get_ach, RequestSchema()),
    Route("GET", "/api/prompts", _get_prompts, RequestSchema(), response_schema=ResponseSchema("object", ("prompts",))),
    Route("GET", "/api/plan/models", _get_plan_models, RequestSchema(), ResponseSchema("object", ("models",))),
    Route("GET", "/api/models", _get_models, RequestSchema(), ResponseSchema("object", ("providers", "default_model"))),
    Route(
        "GET",
        "/api/agent",
        _get_agent,
        RequestSchema(),
        ResponseSchema(
            "object",
            (
                "catalog",
                "presets",
                "simple",
                "profile",
                "proxy_system",
                "proxy_used",
                "proxy_password_set",
                "brave_set",
            ),
        ),
    ),
    Route("GET", "/api/agent/pack", _get_agent_pack, RequestSchema(query=fields(name=("str", "Мой набор")))),
    Route("GET", "/api/learn/live", _get_learn_live, RequestSchema(query=fields(since=("str", "")))),
    Route("GET", "/api/local", _get_local, RequestSchema(query=fields(probe=("any", None)))),
    Route("GET", "/api/sync", _get_sync, RequestSchema(), ResponseSchema("object", ("minutes", "detected", "targets"))),
    Route("GET", "/api/local/heat", _get_local_heat, RequestSchema()),
    Route("GET", "/api/net/detect", _get_net_detect, RequestSchema()),
    Route("GET", "/api/efs", _get_efs, RequestSchema()),
    Route("GET", "/api/crypto", _get_crypto, RequestSchema()),
    Route("GET", "/api/crypto/key", _get_crypto_key, RequestSchema(), ResponseSchema("object", ("key",))),
    Route("GET", "/api/scribe/settings", _get_scribe_settings, RequestSchema()),
    Route("GET", "/api/scribe/status", _get_scribe_status, RequestSchema()),
    Route("GET", "/api/memory/status", _get_memory_status, RequestSchema()),
    Route("GET", "/api/outgoing", _get_outgoing, RequestSchema(query=fields(days=("int", 7)))),
    Route("GET", "/api/telegram", _get_telegram, RequestSchema()),
    Route("GET", "/api/quiz", _get_quiz, RequestSchema()),
    Route("GET", "/api/interview", _get_interview, RequestSchema(), ResponseSchema("object", ("questions",))),
    Route("GET", "/api/telegram/chats", _get_telegram_chats, RequestSchema(), ResponseSchema("object", ("chats",))),
    Route("GET", "/api/obsidian", _get_obsidian, RequestSchema(), ResponseSchema("object", ("vaults", "folders"))),
    Route("GET", "/api/engine", _get_engine, RequestSchema()),
    Route("GET", "/api/learn/brain", _get_learn_brain, RequestSchema()),
    Route("GET", "/api/memory/why", _get_memory_why, RequestSchema(query=fields(text=("str", "")))),
    Route(
        "GET",
        "/api/context",
        _get_context,
        RequestSchema(query=fields(client=("str", "claude"), part=("int", None))),
        response_schema=ResponseSchema("object", ("text", "parts")),
    ),
    Route("GET", "/api/now", _get_now, RequestSchema(), response_schema=ResponseSchema("object", ("text",))),
    Route("GET", "/api/notes", _get_notes, RequestSchema(query=fields(scope=("str", None))), ResponseSchema("array")),
    Route("GET", "/api/note", _get_note, RequestSchema(query=fields(rel=("str", "")))),
    Route(
        "GET", "/api/journal", _get_journal, RequestSchema(query=fields(limit=("int", 100))), ResponseSchema("array")
    ),
    Route("GET", "/api/saves", _get_saves, RequestSchema(), response_schema=ResponseSchema("object", ("saves",))),
    Route("GET", "/api/stale", _get_stale, RequestSchema(), response_schema=ResponseSchema("array")),
    Route("GET", "/api/clients", _get_clients, RequestSchema(), response_schema=ResponseSchema("array")),
    Route(
        "GET",
        "/api/learn/status",
        _get_learn_status,
        RequestSchema(),
        ResponseSchema("object", ("memory_on", "settings", "sources", "brains", "modes", "status", "progress")),
    ),
    Route(
        "GET",
        "/api/learn/items",
        _get_learn_items,
        RequestSchema(query=fields(view=("str", "queue"), limit=("int", 200))),
    ),
)

POST_ROUTES: tuple[Route, ...] = (
    Route(
        "POST",
        "/api/app/autostart",
        _post_app_named,
        RequestSchema(body=fields(on=("any", None))),
        ResponseSchema("object", ("desktop",)),
        raw_body=True,
    ),
    Route(
        "POST",
        "/api/app/close_pref",
        _post_app_named,
        RequestSchema(body=fields(value=("any", None))),
        ResponseSchema("object", ("desktop",)),
        raw_body=True,
    ),
    Route(
        "POST",
        "/api/app/vault_open",
        _post_app_named,
        RequestSchema(body=fields(path=("any", None))),
        ResponseSchema("object"),
        raw_body=True,
    ),
    Route(
        "POST",
        "/api/app/vault_forget",
        _post_app_named,
        RequestSchema(body=fields(path=("any", None), delete=("any", None))),
        ResponseSchema("object"),
        raw_body=True,
    ),
    Route(
        "POST",
        "/api/app/vault_rename",
        _post_app_named,
        RequestSchema(body=fields(path=("any", None), name=("any", None))),
        ResponseSchema("object", ("ok",)),
        raw_body=True,
    ),
    Route(
        "POST",
        "/api/app/update_do",
        _post_app_named,
        RequestSchema(body=fields(action=("any", None), on=("any", None))),
        ResponseSchema("object", ("desktop", "available")),
        raw_body=True,
    ),
    Route(
        "POST",
        "/api/app/",
        _post_app_fallback,
        RequestSchema(),
        ResponseSchema("object", ("desktop",)),
        prefix=True,
    ),
    Route(
        "POST",
        "/api/app/create",
        _post_app_create,
        RequestSchema(
            body=fields(path=("any", None), proxy=("any", None), password=("any", None), prefs=("any", None))
        ),
        ResponseSchema("object", ("ok", "path")),
        raw_body=True,
    ),
    Route(
        "POST",
        "/api/app/demo",
        _post_app_demo,
        RequestSchema(body=fields(proxy=("any", None), password=("any", None), prefs=("any", None))),
        ResponseSchema("object", ("ok", "path")),
        raw_body=True,
    ),
    Route(
        "POST",
        "/api/app/open_existing",
        _post_app_open_existing,
        RequestSchema(body=fields(path=("any", None), lang=("any", None))),
        ResponseSchema("object", ("ok", "path")),
        raw_body=True,
    ),
    Route(
        "POST",
        "/api/remember",
        _post_remember,
        RequestSchema(body=fields(fact=("str", ""), where=("str", "inbox"), client=("str", "owner"))),
    ),
    Route(
        "POST", "/api/undo", _post_undo, RequestSchema(body=fields(id=("str", ""))), ResponseSchema("object", ("ok",))
    ),
    Route(
        "POST",
        "/api/saves/restore",
        _post_saves_restore,
        RequestSchema(body=fields(path=("str", ""))),
        response_schema=ResponseSchema("object", ("ok",)),
    ),
    Route(
        "POST",
        "/api/memory/export",
        _post_memory_export,
        RequestSchema(body=fields(path=("str", ""))),
        response_schema=ResponseSchema("object", ("ok",)),
    ),
    Route(
        "POST",
        "/api/note",
        _post_note,
        RequestSchema(body=fields(rel=("str", ""), raw=("any", None), base=("any", None))),
    ),
    Route(
        "POST",
        "/api/clients",
        _post_clients,
        RequestSchema(),
        raw_body=True,
        response_schema=ResponseSchema("object", ("ok",)),
    ),
    Route(
        "POST",
        "/api/chat/send",
        _post_chat_send,
        RequestSchema(
            body=fields(
                text=("str", ""),
                chat=("str", ""),
                model=("str", ""),
                files=("any", None),
                quote=("str", ""),
                web=("bool", None),
                consortium=("any", None),
                terms=("bool", None),
                opener=("bool", False),
                private=("bool", None),
            )
        ),
    ),
    Route("POST", "/api/plan/budget", _post_plan_budget, RequestSchema(body=fields(task=("str", "")))),
    Route(
        "POST",
        "/api/plan/propose",
        _post_plan_propose,
        RequestSchema(
            body=fields(
                task=("str", ""), chat=("str", ""), planner=("str", ""), budget=("any", None), economy=("bool", True)
            )
        ),
    ),
    Route("POST", "/api/plan/run", _post_plan_run, RequestSchema(body=fields(plan=("any", None), chat=("str", "")))),
    Route("POST", "/api/chat/redo", _post_chat_redo, RequestSchema(body=fields(chat=("str", ""), web=("bool", True)))),
    Route(
        "POST",
        "/api/chat/useful",
        _post_chat_useful,
        RequestSchema(body=fields(chat=("str", ""), index=("int", -1), on=("bool", True))),
    ),
    Route("POST", "/api/portrait/refresh", _post_portrait_refresh, RequestSchema(body=fields(force=("bool", False)))),
    Route("POST", "/api/session/new", _post_session_new, RequestSchema(), ResponseSchema("object", ("id", "started"))),
    Route(
        "POST",
        "/api/session/rename",
        _post_session_rename,
        RequestSchema(body=fields(id=("str", ""), name=("str", ""))),
    ),
    Route("POST", "/api/session/delete", _post_session_delete, RequestSchema(body=fields(id=("str", "")))),
    Route("POST", "/api/chat/learn_now", _post_chat_learn_now, RequestSchema(body=fields(id=("str", "")))),
    Route(
        "POST",
        "/api/chat/update",
        _post_chat_update,
        RequestSchema(
            body=fields(
                id=("str", ""),
                title=("any", None),
                pinned=("any", None),
                private=("any", None),
                consortium=("any", None),
            )
        ),
    ),
    Route(
        "POST",
        "/api/chat/regenerate",
        _post_chat_regenerate,
        RequestSchema(body=fields(chat=("str", ""), model=("str", ""))),
    ),
    Route(
        "POST",
        "/api/chat/cons",
        _post_chat_cons,
        RequestSchema(
            body=fields(
                chat=("str", ""), action=("str", ""), members=("any", None), rounds=("any", None), model=("str", "")
            )
        ),
    ),
    Route(
        "POST",
        "/api/vpn",
        _post_vpn,
        RequestSchema(body=fields(action=("str", ""), key=("str", ""), service=("str", ""))),
    ),
    Route("POST", "/api/web/page", _post_web_page, RequestSchema(body=fields(url=("str", "")))),
    Route(
        "POST",
        "/api/chat/action",
        _post_chat_action,
        RequestSchema(body=fields(chat=("str", ""), id=("str", ""), choice=("str", ""))),
    ),
    Route(
        "POST",
        "/api/chat/sudo",
        _post_chat_sudo,
        RequestSchema(body=fields(chat=("str", ""), id=("str", ""), password=("str", ""), choice=("str", "ok"))),
    ),
    Route(
        "POST",
        "/api/files/open",
        _post_files,
        RequestSchema(body=fields(path=("str", ""))),
        ResponseSchema("object", ("ok",)),
    ),
    Route(
        "POST",
        "/api/files/reveal",
        _post_files,
        RequestSchema(body=fields(path=("str", ""))),
        ResponseSchema("object", ("ok",)),
    ),
    Route(
        "POST",
        "/api/chat/stop",
        _post_chat_stop,
        RequestSchema(body=fields(chat=("str", ""))),
        ResponseSchema("object", ("ok",)),
    ),
    Route(
        "POST",
        "/api/chat/delete",
        _post_chat_delete,
        RequestSchema(body=fields(id=("str", ""))),
        ResponseSchema("object", ("ok",)),
    ),
    Route(
        "POST",
        "/api/providers",
        _post_providers,
        RequestSchema(
            body=fields(
                id=("str", ""), endpoint=("any", None), key=("any", None), disabled=("bool", None), folder=("any", None)
            )
        ),
    ),
    Route("POST", "/api/providers/claude_login", _post_providers_claude_login, RequestSchema()),
    Route("POST", "/api/providers/codex_login", _post_providers_codex_login, RequestSchema()),
    Route("POST", "/api/providers/check", _post_providers_check, RequestSchema(body=fields(id=("str", "")))),
    Route("POST", "/api/providers/models", _post_providers_models, RequestSchema(body=fields(id=("str", "")))),
    Route("POST", "/api/telegram", _post_telegram, RequestSchema(), raw_body=True),
    Route(
        "POST", "/api/compare", _post_compare, RequestSchema(body=fields(question=("str", ""), models=("any", None)))
    ),
    Route(
        "POST",
        "/api/quiz",
        _post_quiz,
        RequestSchema(body=fields(id=("str", ""), verdict=("str", ""), text=("str", ""))),
    ),
    Route("POST", "/api/interview", _post_interview, RequestSchema(body=fields(answers=("any", None)))),
    Route(
        "POST",
        "/api/share/save",
        _post_share_save,
        RequestSchema(body=fields(png=("str", ""), name=("str", ""))),
    ),
    Route(
        "POST",
        "/api/settings/reset",
        _post_settings_reset,
        RequestSchema(),
        response_schema=ResponseSchema("object", ("ok",)),
    ),
    Route(
        "POST",
        "/api/agent",
        _post_agent,
        RequestSchema(
            body=fields(
                preset=("any", None), proxy=("any", None), proxy_password=("any", None), brave_key=("any", None)
            )
        ),
        raw_body=True,
    ),
    Route(
        "POST",
        "/api/net/check",
        _post_net_check,
        RequestSchema(body=fields(proxy=("str", ""), password=("any", None))),
    ),
    Route(
        "POST",
        "/api/local/",
        _post_local,
        RequestSchema(
            body=fields(
                id=("any", None),
                model=("any", None),
                path=("any", None),
                url=("any", None),
                claim=("any", None),
                state=("any", None),
            )
        ),
        raw_body=True,
        prefix=True,
    ),
    Route("POST", "/api/ach/seen", _post_ach_seen, RequestSchema(), response_schema=ResponseSchema("object", ("ok",))),
    Route(
        "POST", "/api/ach/event", _post_ach_event, RequestSchema(), response_schema=ResponseSchema("object", ("ok",))
    ),
    Route("POST", "/api/engine", _post_engine, RequestSchema(), raw_body=True),
    Route(
        "POST",
        "/api/crypto",
        _post_crypto,
        RequestSchema(
            body=fields(
                action=("any", None),
                password=("any", None),
                remember=("any", None),
                old=("any", None),
                new=("any", None),
                recovery=("any", None),
            )
        ),
        raw_body=True,
    ),
    Route("POST", "/api/efs", _post_efs, RequestSchema(body=fields(action=("str", "")))),
    Route(
        "POST",
        "/api/sync/",
        _post_sync,
        RequestSchema(
            body=fields(
                kind=("any", None),
                path=("any", None),
                url=("any", None),
                token=("any", None),
                id=("any", None),
                minutes=("any", None),
            )
        ),
        raw_body=True,
        prefix=True,
    ),
    Route(
        "POST",
        "/api/chat/self_ask",
        _post_chat_self_ask,
        RequestSchema(body=fields(chat=("str", ""), i=("int", -1), action=("str", "skip"), text=("str", ""))),
    ),
    Route(
        "POST",
        "/api/prompts/answer",
        _post_prompts_answer,
        RequestSchema(body=fields(chat=("str", ""), choice=("str", "skip"))),
    ),
    Route("POST", "/api/prompts/delete", _post_prompts_delete, RequestSchema(body=fields(file=("str", "")))),
    Route(
        "POST",
        "/api/prompts/open",
        _post_prompts_open,
        RequestSchema(body=fields(file=("str", ""))),
        ResponseSchema("object", ("ok",)),
    ),
    Route(
        "POST",
        "/api/voice/",
        _post_voice,
        RequestSchema(body=fields(lang=("any", None))),
        raw_body=True,
        prefix=True,
    ),
    Route(
        "POST",
        "/api/scribe/",
        _post_scribe,
        RequestSchema(
            body=fields(
                name=("any", None),
                model=("any", None),
                filename=("any", None),
                data=("any", None),
                choice=("any", None),
                remember=("any", None),
                mode=("any", None),
                base=("any", None),
                cloud_model=("any", None),
                key=("any", None),
            )
        ),
        raw_body=True,
        prefix=True,
    ),
    Route(
        "POST",
        "/api/import/chatgpt",
        _post_import_chatgpt,
        RequestSchema(body=fields(data=("str", ""), filename=("str", "conversations.json"))),
    ),
    Route(
        "POST",
        "/api/open_url",
        _post_open_url,
        RequestSchema(body=fields(url=("str", ""))),
        ResponseSchema("object", ("ok",)),
    ),
    Route(
        "POST",
        "/api/memory/open",
        _post_memory_open,
        RequestSchema(),
        response_schema=ResponseSchema("object", ("ok", "folder")),
    ),
    Route("POST", "/api/connect", _post_connect, RequestSchema(body=fields(target=("str", "")))),
    Route(
        "POST",
        "/api/agent/pack",
        _post_agent_pack,
        RequestSchema(),
        raw_body=True,
        response_schema=ResponseSchema("object", ("profile", "catalog")),
    ),
    Route(
        "POST",
        "/api/learn/settings",
        _post_learn_settings,
        RequestSchema(),
        raw_body=True,
        response_schema=ResponseSchema("object", ("settings",)),
    ),
    Route(
        "POST",
        "/api/learn/run",
        _post_learn_run,
        RequestSchema(body=fields(initial=("bool", False), only=("any", None))),
    ),
    Route(
        "POST",
        "/api/learn/review",
        _post_learn_review,
        RequestSchema(
            body=fields(id=("str", ""), action=("str", ""), text=("str", ""), where=("str", ""), chat=("any", None))
        ),
    ),
    Route(
        "POST",
        "/api/learn/review_all",
        _post_learn_review_all,
        RequestSchema(body=fields(action=("str", "keep"), state=("str", "pending"))),
    ),
    Route(
        "POST",
        "/api/learn/test_brain",
        _post_learn_test_brain,
        RequestSchema(),
        raw_body=True,
        response_schema=ResponseSchema("object", ("ok",)),
    ),
)

_ROUTES: dict[str, tuple[Route, ...]] = {"GET": GET_ROUTES, "POST": POST_ROUTES}


def dispatch(vault: Vault, method: str, path: str, query: dict | None = None, body: Any = None):
    """Находит маршрут и выполняет обработчик. Возвращает (код, payload) или None — тогда 404."""
    routes = _ROUTES.get(method)
    if routes is None:
        return None
    for r in routes:  # сначала точные пути
        if not r.prefix and path == r.path:
            return _run(vault, r, path, query, body)
    for r in routes:  # затем префиксы (/api/local/, /api/sync/, ...)
        if r.prefix and path.startswith(r.path):
            return _run(vault, r, path, query, body)
    return None


def _run(vault: Vault, route: Route, path: str, query: dict | None, body: Any):
    schema = route.request_schema
    params = schema.validate(query, body) if schema else {}
    body_norm = body if route.raw_body else (body if isinstance(body, dict) else {})
    ctx = Ctx(path=path, query=query or {}, body=body_norm, params=params)
    return route.handler(vault, ctx)
