"""Local app and API: http://127.0.0.1:7461

Security:
- listens on 127.0.0.1 only;
- every /api/ call needs the X-Mnema-Token header (token lives in <vault>/.mnema/token);
- the Host header must be 127.0.0.1/localhost — blocks DNS-rebinding pages from reading the app;
- no CORS headers: other websites can't read responses.
"""

from __future__ import annotations

import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import osapi
from .http_router import APP_HOOKS as APP_HOOKS, dispatch as _dispatch  # re-export: хуки окна читает desktop.py
from .journal import UndoError
from .memory import PermissionDenied, token
from .vault import Vault

UI = Path(__file__).resolve().parent / "ui" / "index.html"
# APP_HOOKS — хуки окна (show, info, autostart, switch, …): заполняет desktop.py, читает http_router.


def make_handler(vault: Vault, port: int):
    tok = token(vault)
    from . import http_router, net

    http_router.APP_PORT = port  # /api/app/* без окна отвечает этим портом
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
                if not given or not secrets.compare_digest(given, tok):
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

        def _static(self, u, q, tok):
            """Статика View одним местом: index с токеном, /ui/*.css|.js, /i18n/*.json и первые экраны.

            Возвращает (code, body, ctype) или None, когда путь не статика. Пути и содержимое 1:1 с прежним.
            """
            if u.path.startswith("/i18n/") and u.path.endswith(".json"):  # interface translations
                f = UI.parent / "i18n" / Path(u.path).name
                return (
                    200,
                    osapi.os_words(f.read_text(encoding="utf-8")) if f.exists() else "{}",
                    "application/json; charset=utf-8",
                )
            if u.path.startswith("/ui/") and u.path.endswith((".css", ".js")):  # the interface's own files
                f = (UI.parent / u.path[4:]).resolve()
                if UI.parent.resolve() in f.parents and f.is_file():
                    kind = "text/css" if f.suffix == ".css" else "text/javascript"
                    return 200, osapi.os_words(f.read_text(encoding="utf-8")), kind + "; charset=utf-8"
                return 404, {"error": "нет такого файла"}, "application/json; charset=utf-8"
            if u.path in ("/ui/setup.html", "/ui/missing.html"):  # первые экраны — та же статика
                from .static_pages import missing_html, setup_html

                if u.path == "/ui/setup.html":
                    return 200, setup_html(q.get("lang")), "text/html; charset=utf-8"
                return 200, missing_html(q.get("path", ""), q.get("lang", "ru")), "text/html; charset=utf-8"
            if u.path == "/":
                html = osapi.os_words(UI.read_text(encoding="utf-8")).replace("__MNEMA_TOKEN__", tok)
                return 200, html, "text/html; charset=utf-8"
            return None

        # -- routes
        def do_GET(self):
            if not self.guard():
                return
            u = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            try:
                s = self._static(u, q, tok)
                if s:
                    return self.send(*s)
                r = _dispatch(vault, "GET", u.path, q, None)
                if r:
                    return self.send(*r)
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
                r = _dispatch(vault, "POST", u.path, {}, b)
                if r:
                    return self.send(*r)
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
