"""OpenAI's local open-source Sign in with ChatGPT flow for ChatGPT plan usage."""

from __future__ import annotations

import base64
import html
import hashlib
import json
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .. import net
from ..learn import secrets_store
from ..vault import Vault

AUTH = "https://auth.openai.com/api/accounts/authorize"
TOKEN = "https://auth.openai.com/api/accounts/oauth/token"
RESOURCE = "https://api.openai.com/v1"
ISSUER = "https://auth.openai.com"
SCOPES = "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct"
SLOT = "chat.codex.oauth"
HOST_SLOT = "chatgpt.ext_agent_host_id"
GLOBAL_STORE_ID = "mnemai-local-install"
_lock = threading.Lock()
_refresh_lock = threading.Lock()


class AuthError(RuntimeError):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _read(vault: Vault) -> dict:
    raw = secrets_store.get(secrets_store.vault_id(vault), SLOT)
    try:
        value = json.loads(raw) if raw else {}
        return value if isinstance(value, dict) else {}
    except (ValueError, TypeError):
        return {}


def _write(vault: Vault, value: dict) -> None:
    secrets_store.put(secrets_store.vault_id(vault), SLOT, json.dumps(value, separators=(",", ":")))


def _host_id() -> str:
    host_id = secrets_store.get(GLOBAL_STORE_ID, HOST_SLOT)
    if not host_id:
        host_id = f"urn:uuid:{uuid.uuid4()}"
        secrets_store.put(GLOBAL_STORE_ID, HOST_SLOT, host_id)
    return host_id


def account(vault: Vault) -> dict:
    cred = _read(vault)
    if not cred.get("client_id") or not cred.get("refresh_token"):
        return {}
    if "chatgpt.tokens.use.direct" not in (cred.get("scope") or "").split():
        return {}
    return {"type": "chatgpt", "email": cred.get("email", ""), "planType": cred.get("plan_type", "")}


def _request_token(form: dict[str, str]) -> dict:
    req = urllib.request.Request(
        TOKEN,
        data=urllib.parse.urlencode(form).encode("ascii"),
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        method="POST",
    )
    try:
        with net.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # The server may include an OAuth error body.  Preserve only its stable
        # machine code: authorization codes and diagnostics must never reach the UI.
        kind = "http_error"
        try:
            body = json.loads(exc.read().decode("utf-8", "replace"))
            value = body.get("error") if isinstance(body, dict) else ""
            if isinstance(value, dict):
                value = value.get("code") or value.get("type") or ""
            if isinstance(value, str) and value.replace("_", "").replace("-", "").isalnum():
                kind = value[:80]
        except Exception:
            pass
        raise AuthError(f"OpenAI отклонил обмен кода входа ({kind}, HTTP {exc.code}). Начни вход заново.") from exc
    except Exception as exc:
        raise AuthError("Не удалось завершить вход ChatGPT. Повтори подключение.") from exc
    if not isinstance(result, dict) or not result.get("access_token"):
        raise AuthError("OpenAI не вернул токен доступа ChatGPT.")
    return result


def _verify_id_token(token: str, client_id: str, nonce: str) -> dict:
    try:
        head, body, signature = token.split(".")
        header = json.loads(base64.urlsafe_b64decode(head + "=" * (-len(head) % 4)))
        claims = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if header.get("alg") != "RS256" or not header.get("kid"):
            raise AuthError("OpenAI вернул неподдерживаемую подпись входа.")
        req = urllib.request.Request("https://auth.openai.com/.well-known/jwks.json", headers={"Accept": "application/json"})
        with net.urlopen(req, timeout=15) as response:
            keys = json.loads(response.read().decode("utf-8")).get("keys", [])
        jwk = next((key for key in keys if key.get("kid") == header["kid"] and key.get("kty") == "RSA"), None)
        if not jwk:
            raise AuthError("Не удалось проверить подпись входа OpenAI.")
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding, rsa

        public = rsa.RSAPublicNumbers(
            int.from_bytes(base64.urlsafe_b64decode(jwk["e"] + "=" * (-len(jwk["e"]) % 4)), "big"),
            int.from_bytes(base64.urlsafe_b64decode(jwk["n"] + "=" * (-len(jwk["n"]) % 4)), "big"),
        ).public_key()
        public.verify(
            base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4)),
            f"{head}.{body}".encode("ascii"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        if claims.get("iss") != ISSUER or client_id not in ([claims.get("aud")] if isinstance(claims.get("aud"), str) else claims.get("aud", [])):
            raise AuthError("Ответ входа не принадлежит выбранному аккаунту OpenAI.")
        if int(claims.get("exp", 0)) <= int(time.time()) or claims.get("nonce") != nonce or not claims.get("sub"):
            raise AuthError("Сессия входа OpenAI устарела или не прошла проверку.")
        return claims
    except AuthError:
        raise
    except Exception as exc:
        raise AuthError("Не удалось проверить подписанный ответ OpenAI.") from exc


def _finish(vault: Vault, params: dict, pending: dict) -> None:
    if params.get("state", [""])[0] != pending["state"]:
        raise AuthError("Проверка входа не совпала. Начни подключение заново.")
    if params.get("error", [""])[0]:
        raise AuthError("Вход ChatGPT отменён или не разрешён для этого приложения.")
    code = params.get("code", [""])[0]
    client_id = params.get("client_id", [""])[0] or pending.get("client_id", "")
    if not code or not client_id or (pending.get("client_id") and client_id != pending["client_id"]):
        raise AuthError("OpenAI не завершил регистрацию приложения. Попробуй войти снова.")
    # Dynamic registration has completed at this point.  If the one-time code
    # is rejected (for example after a browser retry), OpenAI requires the next
    # attempt to reuse this issued client ID rather than register a second
    # dynamic client.  This draft deliberately contains no access/refresh token,
    # so it is not considered a connected account by account().
    if not pending.get("client_id"):
        _write(
            vault,
            {
                "client_id": client_id,
                "ext_agent_host_id": pending["host_id"],
                "subject": "",
                "email": "",
                "id_token": "",
                "access_token": "",
                "refresh_token": "",
                "scope": "",
            },
        )
    result = _request_token(
        {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "code_verifier": pending["verifier"],
            "redirect_uri": pending["redirect_uri"],
            "resource": RESOURCE,
        }
    )
    scope = result.get("scope", "")
    if "chatgpt.tokens.use.direct" not in scope.split():
        raise AuthError("Вход выполнен, но разрешение использовать подписку ChatGPT не предоставлено.")
    claims = _verify_id_token(result.get("id_token", ""), client_id, pending["nonce"])
    if pending.get("subject") and claims.get("sub") != pending["subject"]:
        raise AuthError("Вошёл другой аккаунт ChatGPT. Текущий вход не заменён.")
    saved = {
        "client_id": client_id,
        "ext_agent_host_id": pending["host_id"],
        "subject": claims["sub"],
        "email": claims.get("email", ""),
        "id_token": result.get("id_token", ""),
        "access_token": result["access_token"],
        "refresh_token": result.get("refresh_token", ""),
        "token_type": result.get("token_type", "Bearer"),
        "expires_at": int(time.time()) + int(result.get("expires_in", 3600)),
        "scope": scope,
        "plan_type": claims.get("https://api.openai.com/auth", {}).get("chatgpt_plan_type", "")
        if isinstance(claims.get("https://api.openai.com/auth"), dict)
        else "",
    }
    if not saved["refresh_token"]:
        raise AuthError("OpenAI не выдал обновляемый токен. Разреши offline_access и повтори вход.")
    _write(vault, saved)


def begin_login(vault: Vault) -> dict:
    """Start the official loopback OAuth flow; the browser opens the returned URL."""
    if not _lock.acquire(blocking=False):
        return {"ok": False, "error": "Вход ChatGPT уже открыт."}
    try:
        old = _read(vault)
        state, nonce, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(32), secrets.token_urlsafe(48)
        host_id = old.get("ext_agent_host_id") or _host_id()
    except Exception as exc:
        _lock.release()
        return {"ok": False, "error": f"Не удалось подготовить защищённый вход ChatGPT: {exc}"}
    pending = {
        "state": state,
        "nonce": nonce,
        "verifier": verifier,
        "host_id": host_id,
        "client_id": old.get("client_id", ""),
        "subject": old.get("subject", ""),
    }

    class Callback(ThreadingHTTPServer):
        daemon_threads = True
        allow_reuse_address = False

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            return

        def do_GET(self):
            if urllib.parse.urlsplit(self.path).path != "/auth/callback":
                self.send_error(404)
                return
            try:
                _finish(vault, urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query), pending)
                text = "ChatGPT подключён к Mnemai. Можно закрыть эту вкладку и вернуться в приложение."
                code = 200
            except Exception as exc:
                text = str(exc)
                code = 400
            raw = ("<!doctype html><meta charset=utf-8><title>Mnemai</title><p>" + html.escape(text) + "</p>").encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)
            self.server.callback_error = text if code != 200 else ""
            self.server.callback_done = True
            threading.Thread(target=self.server.shutdown, daemon=True).start()

    try:
        listener = Callback(("127.0.0.1", 0), Handler)
        redirect_uri = f"http://127.0.0.1:{listener.server_port}/auth/callback"
        pending["redirect_uri"] = redirect_uri
        pending["callback_error"] = ""
        pending["callback_done"] = False
        listener.callback_done = False
        threading.Thread(target=listener.serve_forever, daemon=True, name="mnema-chatgpt-oauth").start()
        challenge = _b64(hashlib.sha256(verifier.encode("ascii")).digest())
        query = {
            "client_id": old.get("client_id") or "dynamic_agent_client",
            "ext_agent_host_id": host_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": SCOPES,
            "resource": RESOURCE,
            "state": state,
            "nonce": nonce,
            "code_challenge_method": "S256",
            "code_challenge": challenge,
        }
        if old.get("client_id"):
            if old.get("id_token"):
                query["id_token_hint"] = old["id_token"]
            if old.get("email"):
                query["login_hint"] = old["email"]
        else:
            query["agent_name_hint"] = "Mnemai"
        url = AUTH + "?" + urllib.parse.urlencode(query)

        def release_when_done():
            deadline = time.monotonic() + 300
            while not getattr(listener, "callback_done", False) and time.monotonic() < deadline:
                time.sleep(0.25)
            if not getattr(listener, "callback_done", False):
                listener.shutdown()
            listener.server_close()
            _lock.release()

        threading.Thread(target=release_when_done, daemon=True, name="mnema-chatgpt-oauth-finish").start()
        return {"ok": True, "url": url}
    except Exception as exc:
        _lock.release()
        return {"ok": False, "error": f"Не удалось начать вход ChatGPT: {exc}"}


def access_token(vault: Vault) -> str:
    with _refresh_lock:
        cred = _read(vault)
        if not cred or "chatgpt.tokens.use.direct" not in (cred.get("scope") or "").split():
            raise AuthError("Подключи подписку ChatGPT кнопкой «Продолжить с ChatGPT».")
        if int(cred.get("expires_at", 0)) <= int(time.time()) + 60:
            result = _request_token(
                {
                    "grant_type": "refresh_token",
                    "client_id": cred["client_id"],
                    "refresh_token": cred["refresh_token"],
                    "resource": RESOURCE,
                }
            )
            if "chatgpt.tokens.use.direct" not in result.get("scope", cred.get("scope", "")).split():
                raise AuthError("Разрешение использовать подписку ChatGPT отозвано. Подключи её снова.")
            cred.update(
                access_token=result["access_token"],
                refresh_token=result.get("refresh_token", cred["refresh_token"]),
                token_type=result.get("token_type", "Bearer"),
                expires_at=int(time.time()) + int(result.get("expires_in", 3600)),
                scope=result.get("scope", cred["scope"]),
            )
            _write(vault, cred)
        return str(cred.get("access_token") or "")
