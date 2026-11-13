"""API for learning: settings, runs with progress, the review queue."""

from __future__ import annotations

import threading

from .learn import engine, settings as S
from .learn.brains import make_brain
from .learn.ledger import Ledger
from .learn.sources import Episode
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
    d["where"] = engine.route(i)  # where it really goes (sensitive → hidden section)
    return d


def get(vault: Vault, path: str, q: dict):
    if path == "/api/learn/status":
        s = S.load(vault)
        st = _state(vault)
        from .agent import profile as P

        return 200, {
            "memory_on": P.memory_on(vault),
            "settings": S.public(s),
            "sources": S.SOURCES,
            "brains": S.BRAINS,
            "modes": S.MODES_RU,
            "status": engine.status(vault),
            "progress": {"running": st["running"], "log": st["log"][-8:], "last": st["last"]},
        }
    if path == "/api/learn/items":
        led = Ledger(vault)
        view = q.get("view", "queue")
        if view == "queue":
            items = led.queue()
        elif view == "learned":
            items = sorted(
                (i for i in led.items if i["state"] in ("written", "confirmed")),
                key=lambda i: i["last_seen"],
                reverse=True,
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
        out = [_item(i) for i in items[: int(q.get("limit", 200))]]
        if view == "queue":  # statuses older than a month: asked, not trusted silently
            from .memory import stale_items

            stale = stale_items(vault)
            counts["stale"] = len(stale)
            out += stale[: int(q.get("limit", 200))]
        return 200, {"items": out, "counts": counts}
    return None


def post(vault: Vault, path: str, b: dict):
    if path == "/api/learn/settings":
        cur = S.load(vault)
        if cur.get("demo"):
            return 403, {"error": "В демо обучение выключено: заведи свою память"}
        s = S.save(vault, S.merge_from_ui(cur, {k: v for k, v in b.items() if k != "demo"}))
        return 200, {"settings": S.public(s)}
    if path == "/api/learn/run":
        return 200, start_run(vault, bool(b.get("initial")), b.get("only"))
    if path == "/api/learn/review" and str(b.get("id", "")).startswith("stale:"):
        from .memory import resolve_stale

        ev = resolve_stale(vault, str(b["id"]), str(b.get("action", "")), str(b.get("text", "")))
        return 200, {"item": {"id": b["id"], "state": "resolved", "event": ev.get("id", "")}}
    if path == "/api/learn/review" and str(b.get("action", "")) == "keep_all":
        # «Запомнить всё»: this fact and every other question about memory that still waits — one answer for all
        if b.get("chat"):
            from .chat import engine as CH

            def clear_asks(c):
                c["learn_asks"] = []
                c.pop("learn_ask", None)

            try:
                CH.modify_chat(vault, str(b["chat"]), clear_asks)
            except KeyError:
                pass
        if b.get("id"):
            try:
                engine.review(vault, str(b["id"]), "keep")
            except KeyError:
                pass
        return 200, {"done": engine.review_all(vault, "keep")}
    if path == "/api/learn/review":
        if b.get("chat"):  # answered under a conversation: this question goes away, the next one in the queue shows
            from .chat import engine as CH

            def drop_ask(c):
                qs = [q for q in (c.get("learn_asks") or []) if q.get("item") != b.get("id")]
                if (
                    c.get("learn_ask")
                    and c["learn_ask"].get("item") != b.get("id")
                    and all(q.get("item") != c["learn_ask"].get("item") for q in qs)
                ):
                    qs.insert(0, c["learn_ask"])
                c["learn_asks"] = qs
                if qs:
                    c["learn_ask"] = qs[0]
                else:
                    c.pop("learn_ask", None)

            try:
                CH.modify_chat(vault, str(b["chat"]), drop_ask)
            except KeyError:
                pass
        it = engine.review(
            vault, str(b.get("id", "")), str(b.get("action", "")), str(b.get("text", "")), str(b.get("where", ""))
        )
        return 200, {"item": _item(it)}
    if path == "/api/learn/review_all":
        n = engine.review_all(vault, str(b.get("action", "keep")), str(b.get("state", "pending")))
        return 200, {"done": n}
    if path == "/api/learn/test_brain":
        s = S.merge_from_ui(S.load(vault), b) if b else S.load(vault)
        try:
            brain = make_brain(s)
            brain.vault = vault
        except Exception as e:  # not filled in yet: say what's missing, don't fail
            return 200, {"ok": False, "error": str(e)[:300]}
        sample = [Episode("test", "t1", "", "Запомни, что я пью кофе без сахара. Решил начать пилот в понедельник.")]
        try:
            got = brain.extract(sample, "")
        except Exception as e:
            return 200, {"ok": False, "error": str(e)[:300]}
        return 200, {"ok": bool(got), "found": [g["text"] for g in got]}
    return None


def on_undo(vault: Vault, event_id: str) -> None:
    """Undoing a learned write in the journal = "no" for that fact: it won't come back."""
    led = Ledger(vault)
    hit = False
    for i in led.items:
        if i.get("event_id") == event_id:
            i.update(state="rejected", decided_by="owner")
            hit = True
    if hit:
        led.save()
