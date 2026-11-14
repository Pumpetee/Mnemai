"""Local app and API: http://127.0.0.1:7461

Security:
- listens on 127.0.0.1 only;
- every /api/ call needs the X-Mnema-Token header (token lives in <vault>/.mnema/token);
- the Host header must be 127.0.0.1/localhost — blocks DNS-rebinding pages from reading the app;
- no CORS headers: other websites can't read responses.
"""

from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .clients import Client, load_clients, save_clients
from .journal import UndoError, events, undo, write_with_journal
from . import __version__, api_chat, api_learn
from .memory import PermissionDenied, context_for, generate_now, remember, token
from .vault import Vault
from . import osapi

UI = Path(__file__).resolve().parent / "ui" / "index.html"
APP_HOOKS: dict = {}  # filled by the desktop program: show, info, autostart, switch
# the owner's notes, not the generated layers (Now, Index), the journal, the saves or service files
EDITABLE = re.compile(
    r"^(?!.*\.\.)(?!.*/\.)(00 Inbox/[^/]+|70 Memory/(Profile|Rules|Thoughts)|70 Memory/Cards/[^/]+|"
    r"20 Projects/[^/]+(/[^/]+)*|30 People/[^/]+|60 Events/[^/]+|80 Meetings/[^/]+(/[^/]+)?|"
    r"90 System/(?:Recipes|Prompts)/[^/]+)\.md$"
)


def make_handler(vault: Vault, port: int):
    tok = token(vault)
    from . import net

    net.load(vault)  # the owner's proxy: every AI, search and download goes through it
    from . import extra

    extra.warm_all(vault)  # the extra memory folders (an Obsidian vault…) are read in the background
    from . import vpnkey  # connected by a VPN key: bring it up again (the port may change)
    import threading as _th

    _th.Thread(target=lambda: vpnkey.resume(vault), daemon=True, name="mnema-vpn").start()
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    class H(BaseHTTPRequestHandler):
        server_version = "mnema"

        def log_message(self, *a):  # quiet
            pass

        # -- helpers
        def send(self, code: int, body, ctype="application/json; charset=utf-8"):
            post = getattr(self, "_post", None)
            if post and code == 200:
                self._post = None
                try:
                    from . import achievements

                    achievements.on_post(vault, *post)
                except Exception:
                    pass
            data = (
                body
                if isinstance(body, bytes)
                else (json.dumps(body, ensure_ascii=False) if not isinstance(body, str) else body).encode("utf-8")
            )
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def body(self) -> dict:
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n).decode("utf-8") or "{}") if n else {}

        def guard(self) -> bool:
            if self.headers.get("Host", "") not in hosts:
                self.send(403, {"error": "bad host"})
                return False
            path = urlparse(self.path).path
            if path.startswith("/api/") and not path.startswith(("/api/ping", "/api/app/")) and not vault.root.exists():
                self.send(
                    503,
                    {
                        "error": f"Папка памяти пропала: {vault.root}. Верни её на место (или подключи диск) и "
                        "перезапусти Mnemai — или выбери другую папку при запуске."
                    },
                )
                return False
            if path.startswith("/api/"):
                given = self.headers.get("X-Mnema-Token")
                if given != tok:
                    self.send(401, {"error": "нужен токен"})
                    return False
                if (
                    not path.startswith(("/api/ping", "/api/app/", "/api/crypto"))
                    and (vault.service / "crypto.json").exists()
                ):
                    from . import crypt

                    if crypt.locked(vault.root):  # encrypted by Mnemai and the password not given yet
                        self.send(423, {"error": "Память зашифрована — введи пароль", "locked": True})
                        return False
            return True

        # -- routes
        def do_GET(self):
            if not self.guard():
                return
            u = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            try:
                if u.path == "/api/ping":
                    from .agent import profile as P

                    return self.send(
                        200,
                        {
                            "ok": True,
                            "version": __version__,
                            "lang": P.load(vault).get("lang") or "en",
                        },
                    )
                if u.path == "/api/app/selftest":  # the built program checks its own parts (CI)
                    from . import crypt, ocr

                    from .learn import tg_api

                    return self.send(
                        200, {"ocr": ocr.selftest(), "crypt": crypt.selftest(), "telegram": tg_api.selftest()}
                    )
                if u.path.startswith("/api/app/"):
                    name = u.path.rsplit("/", 1)[-1]
                    hook = APP_HOOKS.get(name) if name in ("show", "info", "switch", "quit", "vaults") else None
                    return self.send(200, hook() if hook else {"desktop": False, "port": port})
                r = api_chat.get(vault, u.path, q)
                if r:
                    return self.send(*r)
                if u.path.startswith("/api/learn/"):
                    r = api_learn.get(vault, u.path, q)
                    if r:
                        return self.send(*r)
                if u.path.startswith("/i18n/") and u.path.endswith(".json"):  # interface translations
                    f = UI.parent / "i18n" / Path(u.path).name
                    return self.send(
                        200,
                        osapi.os_words(f.read_text(encoding="utf-8")) if f.exists() else "{}",
                        "application/json; charset=utf-8",
                    )
                if u.path.startswith("/ui/") and u.path.endswith((".css", ".js")):  # the interface's own files
                    f = (UI.parent / u.path[4:]).resolve()
                    if UI.parent.resolve() in f.parents and f.is_file():
                        kind = "text/css" if f.suffix == ".css" else "text/javascript"
                        return self.send(200, osapi.os_words(f.read_text(encoding="utf-8")), kind + "; charset=utf-8")
                    return self.send(404, {"error": "нет такого файла"})
                if u.path == "/":
                    html = osapi.os_words(UI.read_text(encoding="utf-8")).replace("__MNEMA_TOKEN__", tok)
                    return self.send(200, html, "text/html; charset=utf-8")
                if u.path == "/api/context":
                    from .agent import profile as P

                    if not P.memory_on(vault):
                        return self.send(200, {"text": "", "parts": 0, "off": True})
                    part = int(q["part"]) if "part" in q else None
                    text, total = context_for(vault, q.get("client", "claude"), part=part)
                    return self.send(200, {"text": text, "parts": total})
                if u.path == "/api/now":
                    return self.send(200, {"text": generate_now(vault)})
                if u.path == "/api/notes":
                    scope = q.get("scope")
                    notes = [n for n in vault.notes() if not scope or n.scope == scope]
                    return self.send(
                        200,
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
                        ],
                    )
                if u.path == "/api/note":
                    rel = q.get("rel", "")
                    if not EDITABLE.match(rel):
                        return self.send(400, {"error": "этот файл нельзя открыть"})
                    raw = vault.read_raw(rel) or ""
                    from .journal import _hash

                    return self.send(200, {"rel": rel, "raw": raw, "hash": _hash(raw)})
                if u.path == "/api/journal":
                    return self.send(200, events(vault, int(q.get("limit", 100))))
                if u.path == "/api/stale":
                    return self.send(
                        200,
                        [
                            {"rel": s.rel, "text": s.text, "age": s.age_days, "date": s.date.isoformat()}
                            for s in vault.stale()
                        ],
                    )
                if u.path == "/api/clients":
                    return self.send(200, [c.__dict__ for c in load_clients(vault).values()])
                return self.send(404, {"error": "нет такого пути"})
            except (KeyError, ValueError) as e:
                return self.send(400, {"error": str(e).strip("'")})
            except Exception as e:
                return self.send(500, {"error": str(e)})

        def do_POST(self):
            if not self.guard():
                return
            u = urlparse(self.path)
            try:
                b = self.body()
                self._post = (u.path, b)
                if u.path == "/api/remember":
                    from .agent import profile as P

                    if not P.memory_on(vault):
                        return self.send(409, {"error": P.MEMORY_OFF, "off": True})
                    ev = remember(
                        vault, str(b.get("fact", "")), str(b.get("where", "inbox")), str(b.get("client", "owner"))
                    )
                    return self.send(200, {"id": ev["id"], "path": ev["paths"][0]})
                if u.path.startswith("/api/app/"):
                    name = u.path.rsplit("/", 1)[-1]
                    hook = (
                        APP_HOOKS.get(name)
                        if name in ("autostart", "close_pref", "vault_open", "vault_forget", "vault_rename")
                        else None
                    )
                    return self.send(200, hook(b) if hook else {"desktop": False})
                r = api_chat.post(vault, u.path, b if isinstance(b, dict) else {})
                if r:
                    return self.send(*r)
                if u.path.startswith("/api/learn/"):
                    r = api_learn.post(vault, u.path, b if isinstance(b, dict) else {})
                    if r:
                        return self.send(*r)
                if u.path == "/api/undo":
                    ev = undo(vault, str(b.get("id", "")))
                    api_learn.on_undo(vault, str(b.get("id", "")))
                    return self.send(200, {"ok": True, "summary": ev["summary"]})
                if u.path == "/api/note":
                    rel, raw = str(b.get("rel", "")), b.get("raw")
                    if not EDITABLE.match(rel) or not isinstance(raw, str):
                        return self.send(400, {"error": "этот файл нельзя править"})
                    from .journal import _hash

                    with vault.lock():
                        if b.get("base") and _hash(vault.read_raw(rel) or "") != b["base"]:
                            return self.send(
                                409,
                                {
                                    "error": "Файл изменился, пока ты его правил: Mnemai дописала в него новое. "
                                    "Открой его заново и повтори правку."
                                },
                            )
                        ev = write_with_journal(vault, "owner", rel, raw, f"правка вручную: {rel}")
                    generate_now(vault)
                    return self.send(200, {"id": ev["id"]})
                if u.path == "/api/clients":
                    items = b if isinstance(b, list) else b.get("clients", [])
                    clients = {}
                    for it in items:
                        known = {k: v for k, v in it.items() if k in Client.__dataclass_fields__}
                        c = Client(**known)
                        clients[c.id] = c
                    if not clients:
                        return self.send(400, {"error": "пустой список"})
                    save_clients(vault, clients)
                    return self.send(200, {"ok": True})
                return self.send(404, {"error": "нет такого пути"})
            except PermissionDenied as e:
                return self.send(403, {"error": str(e)})
            except (UndoError, ValueError, KeyError) as e:
                return self.send(400, {"error": str(e).strip("'")})
            except Exception as e:
                return self.send(500, {"error": str(e)})

    return H


def make_server(vault: Vault, port: int = 7461) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), make_handler(vault, port))


def serve(vault: Vault, port: int = 7461, learn: bool = True) -> None:
    srv = make_server(vault, port)
    if learn:
        from .learn.engine import Learner

        Learner(vault).start()
        from .sync import Syncer

        Syncer(vault).start()
        from . import tasks

        tasks.start_worker(vault)
    from .chat import engine as CH
    import threading as _th

    _th.Thread(target=CH.resume_queues, args=(vault,), daemon=True, name="mnema-resume-queue").start()
    print(f"Mnemai: http://127.0.0.1:{port}  (хранилище {vault.root})", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
