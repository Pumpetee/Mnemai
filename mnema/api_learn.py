"""API для обучения: настройки, прогоны с прогрессом, очередь ревью.

Все маршруты «if path == ...» перенесены в декларативный роутер (mnema/http_router.py);
здесь остались состояние прогонов и точки вызова get/post для тестов.
"""

from __future__ import annotations

import threading

from .learn import engine
from .learn.ledger import Ledger
from .vault import Vault

_progress: dict[str, dict] = {}


def _state(vault: Vault) -> dict:
    return _progress.setdefault(str(vault.root), {"running": False, "log": [], "last": None})


def start_run(vault: Vault, initial: bool = False, only: list | None = None) -> dict:
    st = _state(vault)
    if st["running"]:
        return {"started": False, "error": "уже учится"}
    st.update(running=True, log=[], last=None)

    def work():
        try:
            st["last"] = engine.run(vault, initial=initial, only=only, progress=lambda m: st["log"].append(m))
        except Exception as e:
            st["last"] = {"errors": [str(e)]}
        finally:
            st["running"] = False

    threading.Thread(target=work, daemon=True).start()
    return {"started": True}


def _item(i: dict) -> dict:
    d = {
        k: i.get(k)
        for k in (
            "id",
            "text",
            "kind",
            "where",
            "tags",
            "confidence",
            "count",
            "sources",
            "evidence",
            "contradicts",
            "state",
            "first_seen",
            "last_seen",
            "correction",
        )
    }
    d["where"] = engine.route(i)  # куда на самом деле уходит факт (личное → скрытый раздел)
    return d


def get(vault: Vault, path: str, q: dict):
    """GET-маршруты обучения: делегирование декларативному роутеру (прежняя точка вызова)."""
    from .http_router import dispatch

    return dispatch(vault, "GET", path, q, None)


def post(vault: Vault, path: str, b: dict):
    """POST-маршруты обучения: делегирование декларативному роутеру (прежняя точка вызова)."""
    from .http_router import dispatch

    return dispatch(vault, "POST", path, {}, b)


def on_undo(vault: Vault, event_id: str) -> None:
    """Undoing a learned write in the journal = "no" for that fact: it won't come back."""
    with engine._lock:  # owner decisions must never be lost to a learning pass writing the ledger in parallel
        led = Ledger(vault)
        hit = False
        for i in led.items:
            if i.get("event_id") == event_id:
                i.update(state="rejected", decided_by="owner")
                hit = True
        if hit:
            led.save()
