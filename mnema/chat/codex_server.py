"""Small stdio client for Codex App Server using Mnemai's own ChatGPT-plan OAuth token."""

from __future__ import annotations

import json
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable

from .. import net


class CodexError(RuntimeError):
    def __init__(self, message: str, code: str = ""):
        super().__init__(message)
        self.code = code


def executable() -> str:
    """Find the native CLI executable; on Windows avoid PowerShell/npm command shims."""
    exe = shutil.which("codex.exe") if sys.platform == "win32" else shutil.which("codex")
    return exe or ""


class AppServer:
    def __init__(self, token: str, timeout: float = 90):
        exe = executable()
        if not exe:
            raise CodexError("Codex App Server недоступен. Установи Codex CLI и перезапусти Mnemai.", "missing")
        self.timeout = timeout
        config = [
            "-c",
            'model_provider="openai_chatgpt_plan"',
            "-c",
            'model_providers.openai_chatgpt_plan.name="ChatGPT plan"',
            "-c",
            'model_providers.openai_chatgpt_plan.base_url="https://api.openai.com/v1"',
            "-c",
            'model_providers.openai_chatgpt_plan.env_key="ACCESS_TOKEN"',
            "-c",
            'model_providers.openai_chatgpt_plan.wire_api="responses"',
            "-c",
            "model_providers.openai_chatgpt_plan.requires_openai_auth=false",
            "-c",
            "model_providers.openai_chatgpt_plan.supports_websockets=false",
            "-c",
            "mcp_servers={}",
        ]
        self.codex_home = tempfile.TemporaryDirectory(prefix="mnema-codex-home-")
        try:
            self.proc = subprocess.Popen(
                [exe, "app-server", "--listen", "stdio://", *config],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=tempfile.gettempdir(),
                env=net.env(
                    {
                        "ACCESS_TOKEN": token,
                        "CODEX_HOME": self.codex_home.name,
                        "GIT_CEILING_DIRECTORIES": tempfile.gettempdir(),
                    }
                ),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception:
            self.codex_home.cleanup()
            raise
        self.lines: queue.Queue = queue.Queue()
        self._id = 0
        self._write_lock = threading.Lock()
        self._reader = threading.Thread(target=self._read, daemon=True, name="mnema-codex-rpc")
        self._reader.start()

    def _read(self):
        try:
            assert self.proc.stdout is not None
            for raw in self.proc.stdout:
                try:
                    self.lines.put(json.loads(raw.decode("utf-8", "replace")))
                except (ValueError, UnicodeError):
                    continue
        finally:
            self.lines.put(None)

    def send(self, payload: dict):
        if self.proc.poll() is not None:
            raise CodexError("Codex App Server завершился. Проверь установку Codex.", "server")
        try:
            data = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
            with self._write_lock:
                assert self.proc.stdin is not None
                self.proc.stdin.write(data)
                self.proc.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise CodexError("Не удалось связаться с Codex App Server.", "server") from exc

    def _next(self, deadline: float) -> dict:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise CodexError("Codex не ответил вовремя. Повтори попытку.", "timeout")
        try:
            item = self.lines.get(timeout=remaining)
        except queue.Empty as exc:
            raise CodexError("Codex не ответил вовремя. Повтори попытку.", "timeout") from exc
        if item is None:
            raise CodexError("Codex App Server неожиданно завершился.", "server")
        return item

    def request(
        self,
        method: str,
        params: dict | None = None,
        on_message: Callable[[dict], None] | None = None,
        timeout: float | None = None,
    ):
        self._id += 1
        req_id = self._id
        self.send({"method": method, "id": req_id, "params": params or {}})
        deadline = time.monotonic() + (timeout or self.timeout)
        while True:
            msg = self._next(deadline)
            if msg.get("id") == req_id:
                if "error" in msg:
                    err = msg.get("error") or {}
                    raise CodexError(str(err.get("message") or "ошибка протокола Codex"), str(err.get("code", "")))
                return msg.get("result") or {}
            if "id" in msg and "method" in msg:  # Never approve a server-initiated operation.
                self.send({"id": msg["id"], "error": {"code": -32000, "message": "Mnemai does not approve tools"}})
            elif on_message:
                on_message(msg)

    def start(self):
        from .. import __version__

        self.request(
            "initialize",
            {"clientInfo": {"name": "Mnemai", "title": "Mnemai", "version": __version__}},
        )
        self.send({"method": "initialized", "params": {}})

    def close(self):
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
        except OSError:
            pass
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=3)
        self._reader.join(timeout=2)
        try:
            if self.proc.stdout:
                self.proc.stdout.close()
        except OSError:
            pass
        self.codex_home.cleanup()

    def __enter__(self):
        try:
            self.start()
            return self
        except Exception:
            self.close()
            raise

    def __exit__(self, *_):
        self.close()


def account(vault) -> dict:
    from . import codex_auth as auth

    return auth.account(vault)


def models(vault) -> list[dict]:
    from . import codex_auth as auth

    token = auth.access_token(vault)
    with AppServer(token) as server:
        rows, cursor = [], None
        while True:
            params = {"limit": 100, "includeHidden": False}
            if cursor:
                params["cursor"] = cursor
            page = server.request("model/list", params)
            rows.extend(page.get("data") or [])
            cursor = page.get("nextCursor")
            if not cursor or len(rows) >= 400:
                break
        return [m for m in rows if m.get("id") and not m.get("hidden")]


def login(vault) -> dict:
    from . import codex_auth as auth

    return auth.begin_login(vault)


def _plain_history(system: str, messages: list[dict]) -> str:
    rows = ["Ты отвечаешь в приложении Mnemai. Действуй только как собеседник: не запускай команды и не используй инструменты."]
    if system:
        rows.extend(("Инструкции Mnemai:", system))
    for msg in messages:
        role = "Пользователь" if msg.get("role") == "user" else "Ассистент"
        rows.append(f"{role}:\n{msg.get('text') or ''}")
        for f in msg.get("files") or []:
            if f.get("kind") in ("image", "pdf"):
                rows.append(f"[Вложение недоступно провайдеру Codex: {Path(str(f.get('path') or '')).name}]")
    return "\n\n".join(rows)


def stream(vault, model: str, system: str, messages: list[dict], stop=None, timeout: float = 600):
    """Stream one read-only Codex turn with the app's own authorized ChatGPT-plan token."""
    from . import codex_auth as auth

    token = auth.access_token(vault)
    with AppServer(token, timeout=timeout) as server:
        with tempfile.TemporaryDirectory(prefix="mnema-codex-") as cwd:
            thread = server.request(
                "thread/start",
                {"model": model, "cwd": cwd, "approvalPolicy": "never", "sandbox": "read-only"},
            ).get("thread") or {}
            thread_id = thread.get("id")
            if not thread_id:
                raise CodexError("Codex не создал разговор.", "server")
            got = False
            pending_events: list[dict] = []
            deadline = time.monotonic() + timeout

            def on_message(msg):
                pending_events.append(msg)

            def take_event():
                if pending_events:
                    return pending_events.pop(0)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise CodexError("Codex не завершил ответ вовремя. Повтори попытку.", "timeout")
                try:
                    item = server.lines.get(timeout=min(0.25, remaining))
                except queue.Empty:
                    return {}
                if item is None:
                    raise CodexError("Codex App Server неожиданно завершился.", "server")
                return item

            try:
                server.request(
                    "turn/start",
                    {
                        "threadId": thread_id,
                        "input": [{"type": "text", "text": _plain_history(system, messages)}],
                        "cwd": cwd,
                        "approvalPolicy": "never",
                        "sandboxPolicy": {
                            "type": "readOnly",
                            "access": {"type": "restricted", "readableRoots": [cwd]},
                        },
                        **({"model": model} if model else {}),
                    },
                    on_message=on_message,
                )
                while True:
                    if stop and stop():
                        server.send({"method": "turn/interrupt", "id": 999999, "params": {"threadId": thread_id}})
                        return
                    msg = take_event()
                    method = msg.get("method")
                    if method == "item/agentMessage/delta":
                        piece = str((msg.get("params") or {}).get("delta") or "")
                        if piece:
                            got = True
                            yield piece
                    elif method == "item/completed":
                        item = (msg.get("params") or {}).get("item") or {}
                        if item.get("type") == "agentMessage" and not got and item.get("text"):
                            got = True
                            yield str(item["text"])
                    elif method == "turn/completed":
                        turn = (msg.get("params") or {}).get("turn") or {}
                        if turn.get("status") != "completed":
                            err = turn.get("error") or {}
                            info = str(err.get("message") or err.get("codexErrorInfo") or turn.get("status") or "")
                            code = str(err.get("codexErrorInfo") or "")
                            if code == "usageLimitExceeded" or "limit" in info.lower():
                                raise CodexError("Достигнут лимит использования Codex по подписке. Попробуй позже.", "limit")
                            raise CodexError(f"Codex не завершил ответ: {info[:240]}", code or "turn")
                        if not got:
                            raise CodexError("Codex завершил запрос без текстового ответа.", "empty")
                        return
                    elif "id" in msg and "method" in msg:
                        server.send({"id": msg["id"], "error": {"code": -32000, "message": "Mnemai does not approve tools"}})
            finally:
                try:
                    server.request("thread/delete", {"threadId": thread_id}, timeout=5)
                except Exception:  # noqa: BLE001 — do not mask the actual answer or failure
                    pass
