"""Durable tasks: a small persistent queue for MCP clients and a background worker.

A task is a prompt for Mnemai. `auto` tasks are picked up by the worker (in the running app), with priority,
dependencies and bounded retries; they survive restarts. Tasks without `auto` are just a checklist and are run
only when the client calls task_run.
"""

from __future__ import annotations

import json
import os
import secrets
import threading
import time
from pathlib import Path

from .journal import log_event
from .vault import Vault

WORKER_EVERY = 5.0
MAX_ATTEMPTS = 3
_started: set[str] = set()
_lock = threading.Lock()


def path(vault: Vault) -> Path:
    vault.service.mkdir(parents=True, exist_ok=True)
    return vault.service / "tasks.json"


def load(vault: Vault) -> list[dict]:
    try:
        data = json.loads(path(vault).read_text(encoding="utf-8"))
        return [x for x in data if isinstance(x, dict)]
    except (OSError, ValueError):
        return []


def save(vault: Vault, items: list[dict]) -> None:
    path(vault).write_text(json.dumps(items[:1000], ensure_ascii=False, indent=1), encoding="utf-8")


def add(
    vault: Vault,
    text: str,
    *,
    priority: str = "normal",
    depends_on: str = "",
    auto: bool = False,
    model: str = "",
    client: str = "owner",
) -> dict:
    text = " ".join(str(text).split())
    if not text:
        raise ValueError("нужен текст задачи")
    with _lock:
        items = load(vault)
        if depends_on and not any(x.get("id") == depends_on for x in items):
            raise ValueError("зависимость не найдена")
        item = {
            "id": secrets.token_hex(4),
            "text": text,
            "priority": priority if priority in ("low", "normal", "high") else "normal",
            "status": "open",
            "depends_on": depends_on,
            "auto": bool(auto),
            "model": str(model or ""),
            "created": time.time(),
            "updated": time.time(),
            "attempts": 0,
            "error": "",
            "result": "",
            "chat": "",
        }
        items.append(item)
        save(vault, items)
    log_event(vault, client, "write", f"задача: {text[:160]}")
    return item


def get(vault: Vault, tid: str) -> dict | None:
    return next((x for x in load(vault) if x.get("id") == tid), None)


def _alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def update(vault: Vault, tid: str, **fields) -> dict:
    with _lock:
        items = load(vault)
        task = next((x for x in items if x.get("id") == tid), None)
        if not task:
            raise ValueError("такой задачи нет")
        for k in ("text", "priority", "status", "auto", "model", "error", "result", "chat", "attempts", "runner"):
            if k in fields:
                task[k] = fields[k]
        task["updated"] = time.time()
        save(vault, items)
    return task


def remove(vault: Vault, tid: str) -> dict:
    with _lock:
        items = load(vault)
        task = next((x for x in items if x.get("id") == tid), None)
        if not task:
            raise ValueError("такой задачи нет")
        items.remove(task)
        save(vault, items)
    return task


def ready(vault: Vault, task: dict, items: list[dict]) -> bool:
    dep = task.get("depends_on") or ""
    if not dep:
        return True
    return any(x.get("id") == dep and x.get("status") == "done" for x in items)


def run(vault: Vault, tid: str, client: str = "owner") -> str:
    from .chat import engine as CH

    task = get(vault, tid)
    if not task:
        raise ValueError("такой задачи нет")
    if task.get("status") == "running":
        raise ValueError("эта задача уже выполняется")
    update(vault, tid, status="running", error="", runner=os.getpid())
    try:
        r = CH.send(vault, task["text"], model=task.get("model") or "", sync=True, learn=False)
        chat = CH.load_chat(vault, r["chat"])
        answer = next((m.get("text") for m in reversed(chat.get("messages", [])) if m.get("role") == "assistant"), "")
        update(
            vault,
            tid,
            status="done",
            result=answer[-2000:],
            chat=r["chat"],
            attempts=int(task.get("attempts") or 0) + 1,
        )
        log_event(vault, client, "exec", f"задача {tid} выполнена")
        return f"Задача {tid} выполнена: {answer[:800]}"
    except Exception as e:  # noqa: BLE001 — a task failure is data, not a crash
        attempts = int(task.get("attempts") or 0) + 1
        status = "open" if attempts < MAX_ATTEMPTS else "failed"
        update(vault, tid, status=status, attempts=attempts, error=str(e)[:1000])
        log_event(vault, client, "exec", f"задача {tid} сорвалась: {str(e)[:200]}")
        raise


def start_worker(vault: Vault) -> None:
    """One background worker per vault: runs `auto` tasks in priority order, retries up to MAX_ATTEMPTS."""
    key = str(vault.root.resolve())
    if key in _started:
        return
    _started.add(key)

    def loop() -> None:
        while True:
            did = False
            try:
                items = load(vault)
                # a worker killed mid-task leaves running; give it back to the queue
                changed = False
                for t in items:
                    if t.get("status") == "running":
                        runner = int(t.get("runner") or 0)
                        stale = time.time() - float(t.get("updated") or 0) > 3600
                        if stale or not _alive(runner):  # another live MCP process may own it
                            t["status"] = "open"
                            t["runner"] = 0
                            changed = True
                if changed:
                    save(vault, items)
                ordered = sorted(
                    [x for x in items if x.get("status") == "open" and x.get("auto")],
                    key=lambda x: (x.get("priority") != "high", float(x.get("created") or 0)),
                )
                for task in ordered:
                    if ready(vault, task, load(vault)):
                        did = True
                        try:
                            run(vault, str(task["id"]), client="worker")
                        except Exception:  # noqa: BLE001
                            pass
                        break
            except Exception:  # noqa: BLE001 — the worker must never kill the app
                pass
            if not did:  # ready tasks are drained back-to-back; only an idle queue sleeps
                time.sleep(WORKER_EVERY)

    threading.Thread(target=loop, daemon=True, name="mnema-tasks").start()
