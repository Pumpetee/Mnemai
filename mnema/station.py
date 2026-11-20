"""Mnemai station: the owner's own server with a copy of the memory.

- computers sync with it (sync.py, target "station") — access is by the owner's password (BP-13, decision of
  20.11.2026: a personal server, password auth, no roles); the password travels in the Authorization header
  and is stored here only as a salted hash;
- any agent or AI that speaks MCP connects over HTTP (POST /mcp, JSON-RPC); the owner's password gives the
  full access of the local assistant, legacy per-assistant MCP keys keep working.

Run on a server:  MNEMA_STATION_PASSWORD=<пароль> mnema --vault /srv/mnema station --host 0.0.0.0 --port 8765
New MCP key:      mnema --vault /srv/mnema station-key --client claude
Put it behind HTTPS (Caddy, nginx): the password travels in the Authorization header.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .memory import init_vault
from .sync import local_files, wanted
from .vault import Vault


def _keys_file(vault: Vault):
    return vault.service / "station.json"


def keys(vault: Vault) -> dict:
    f = _keys_file(vault)
    data = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    if not data.get("sync"):
        data["sync"] = secrets.token_urlsafe(32)
        data.setdefault("mcp", {})
        vault.service.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(data, indent=1), encoding="utf-8")
    return data


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + ":" + password).encode("utf-8")).hexdigest()


def set_password(vault: Vault, password: str) -> None:
    """The owner's password for the station (BP-13: access by password, no roles). Stored only as a salted hash."""
    data = keys(vault)
    if password:
        salt = secrets.token_hex(8)
        data["password"] = {"salt": salt, "hash": _hash_password(password, salt)}
    else:
        data.pop("password", None)
    _keys_file(vault).write_text(json.dumps(data, indent=1), encoding="utf-8")


def check_password(vault: Vault, tok: str) -> bool:
    p = keys(vault).get("password")
    return bool(p and tok and secrets.compare_digest(_hash_password(tok, p.get("salt", "")), p.get("hash", "")))


def new_mcp_key(vault: Vault, client: str) -> str:
    data = keys(vault)
    k = secrets.token_urlsafe(32)
    data.setdefault("mcp", {})[k] = client
    _keys_file(vault).write_text(json.dumps(data, indent=1), encoding="utf-8")
    return k


def make_handler(vault: Vault):
    from .mcp_server import Server

    class H(BaseHTTPRequestHandler):
        server_version = "MnemaStation"

        def log_message(self, *a):
            pass

        def _send(self, code: int, body, ctype: str = "application/json; charset=utf-8"):
            data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _who(self) -> str:
            """ "owner" for the owner's password, "sync" for the legacy sync key, an assistant id for an MCP key, "" otherwise.

            The client sends the password base64-encoded (HTTP headers are latin-1); an ASCII password or key
            may arrive as is."""
            auth = self.headers.get("Authorization", "")
            tok = auth[7:].strip() if auth.startswith("Bearer ") else ""
            if not tok:
                return ""
            plain = tok
            try:
                decoded = base64.urlsafe_b64decode(tok + "=" * (-len(tok) % 4)).decode("utf-8")
            except Exception:
                decoded = ""
            for candidate in (decoded, plain):
                if candidate and check_password(vault, candidate):
                    return "owner"
            k = keys(vault)
            for candidate in (decoded, plain):
                if candidate and secrets.compare_digest(candidate, k["sync"]):
                    return "sync"
            for key, client in (k.get("mcp") or {}).items():
                if secrets.compare_digest(plain, key) or (decoded and secrets.compare_digest(decoded, key)):
                    return "mcp:" + client
            return ""

        def _rel(self) -> str | None:
            rel = (parse_qs(urlparse(self.path).query).get("rel") or [""])[0]
            if not rel or not wanted(rel):
                return None
            try:
                vault.path(rel)
            except ValueError:
                return None
            return rel

        def _body(self) -> bytes:
            n = int(self.headers.get("Content-Length") or 0)
            if n > 50 * 1024 * 1024:
                raise ValueError("слишком большой файл")
            return self.rfile.read(n)

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/health":
                return self._send(200, {"ok": True})
            if self._who() not in ("sync", "owner"):
                return self._send(401, {"error": "нужен пароль владельца или ключ синхронизации"})
            if path == "/sync/list":
                return self._send(200, local_files(vault.root))
            if path == "/sync/file":
                rel = self._rel()
                if rel is None or not vault.path(rel).exists():
                    return self._send(404, {"error": "нет такого файла"})
                return self._send(200, vault.path(rel).read_bytes(), "application/octet-stream")
            return self._send(404, {"error": "не найдено"})

        def do_PUT(self):
            if self._who() not in ("sync", "owner") or urlparse(self.path).path != "/sync/file":
                return self._send(401, {"error": "нужен пароль владельца или ключ синхронизации"})
            rel = self._rel()
            if rel is None:
                return self._send(400, {"error": "этот файл не синхронизируется"})
            p = vault.path(rel)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(self._body())
            return self._send(200, {"ok": True})

        def do_DELETE(self):
            if self._who() not in ("sync", "owner") or urlparse(self.path).path != "/sync/file":
                return self._send(401, {"error": "нужен пароль владельца или ключ синхронизации"})
            rel = self._rel()
            if rel is None:
                return self._send(400, {"error": "этот файл не синхронизируется"})
            vault.path(rel).unlink(missing_ok=True)
            return self._send(200, {"ok": True})

        def do_POST(self):
            if urlparse(self.path).path != "/mcp":
                return self._send(404, {"error": "не найдено"})
            who = self._who()
            if who == "owner":  # the owner's password: the local assistant sees everything
                srv = Server(vault, "local")
            elif who.startswith("mcp:"):
                srv = Server(vault, who[4:])
            else:
                return self._send(401, {"error": "нужен пароль владельца или MCP-ключ станции"})
            try:
                msg = json.loads(self._body() or b"{}")
            except ValueError:
                return self._send(
                    400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
                )
            if isinstance(msg, list):
                out = [r for r in (srv.handle(m) for m in msg) if r]
            else:
                out = srv.handle(msg)
            if not out:
                self.send_response(202)
                self.end_headers()
                return
            return self._send(200, out)

    return H


def make_server(vault: Vault, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    if not vault.exists():
        init_vault(vault)
    keys(vault)
    return ThreadingHTTPServer((host, port), make_handler(vault))


def serve(vault: Vault, host: str, port: int, password: str = "") -> None:
    """The station process. The owner's password comes from the argument or MNEMA_STATION_PASSWORD (BP-13:
    access by password, no roles); without it the station keeps working on the legacy sync key."""
    if not password:
        password = os.environ.get("MNEMA_STATION_PASSWORD", "")
    if password:
        set_password(vault, password)
    srv = make_server(vault, host, port)
    k = keys(vault)
    print(f"Mnemai station: http://{host}:{port}")
    if k.get("password"):
        print("Доступ — по паролю владельца (Authorization: Bearer <пароль>).")
    else:
        print(f"Ключ синхронизации (вставь в Mnemai → Настройки → Синхронизация): {k['sync']}")
    print("MCP-ключ для агента: mnema station-key --client claude")
    srv.serve_forever()
