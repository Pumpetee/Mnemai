"""Ledger: everything Mnemai ever learned or considered, with how sure it is and what the owner decided.

States
  weak            seen, not sure yet — waits for the fact to repeat (not shown in the queue)
  observed        source is in "observe" mode — shown, never written
  pending         waiting for the owner in the review queue
  conflict        contradicts what memory already says — the owner picks
  written         in memory, learned automatically, not confirmed
  confirmed       in memory, the owner approved or edited it
  forget_pending  learned once, never repeated or confirmed for a long time — offered to forget
  forgotten       removed from memory at the owner's word
  rejected        the owner said no — never asked again
"""

from __future__ import annotations

import datetime as dt
import difflib
import json
import re
import secrets
from pathlib import Path

from ..vault import Vault

QUEUE_STATES = {"pending", "conflict", "forget_pending", "asking"}
# states the old design parked in the queue forever: on load they go back to "wait to be seen again".
# "asking" is different — it waits for the owner's word under the conversation and must survive a reload.
LEGACY_QUEUE = {"pending", "conflict", "forget_pending"}
IN_MEMORY = {"written", "confirmed"}


def _file(vault: Vault) -> Path:
    return vault.service / "learn" / "ledger.json"


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def norm(t: str) -> str:
    t = re.sub(r"\((?:статус|status)[^()]*\)|\d{1,2}\.\d{1,2}\.\d{4}|· выучено", " ", t.lower())
    return " ".join(re.sub(r"[^\w\s]", " ", t).split())


def similar(a: str, b: str) -> float:
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    m = difflib.SequenceMatcher(None, a, b)
    return m.ratio() if m.real_quick_ratio() >= 0.6 and m.quick_ratio() >= 0.6 else 0.0


STOP_STEMS = {
    "давай",
    "делай",
    "пиши",
    "нужно",
    "надо",
    "всегда",
    "чтобы",
    "когда",
    "только",
    "очень",
    "можно",
    "будет",
    "этого",
    "этот",
    "такой",
}


def stems(t: str) -> set:
    """Word stems of a rule: the first five letters of words from four letters, without filler."""
    return {w[:5] for w in re.findall(r"[a-zа-яё]{4,}", norm(t)) if w[:5] not in STOP_STEMS}


def same_meaning(a: str, b: str) -> bool:
    """Two wordings of one rule: most stems of the shorter one are in the other ("Сводку переписки давай коротко,
    по пунктам" and "Делай сводки переписки короткими и по пунктам")."""
    sa, sb = stems(a), stems(b)
    if min(len(sa), len(sb)) < 2:
        return False
    return len(sa & sb) / min(len(sa), len(sb)) >= 0.6


def combined(confs: list[float]) -> float:
    """Independent sightings add up: two 0.6 → 0.84, three → 0.94."""
    p = 1.0
    for c in confs:
        p *= 1 - c
    return round(1 - p, 3)


def said_date(ts) -> dt.date | None:
    """The local day of a source timestamp ("2026-09-21T13:16:01.464Z", "2026-09-21 16:16", ...). None if unknown or future."""
    if not ts:
        return None
    try:
        t = dt.datetime.fromisoformat(str(ts).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo:
        t = t.astimezone().replace(tzinfo=None)
    d = t.date()
    return d if d <= dt.date.today() else None


class Ledger:
    def __init__(self, vault: Vault):
        self.vault = vault
        f = _file(vault)
        self.items: list[dict] = json.loads(f.read_text(encoding="utf-8"))["items"] if f.exists() else []
        for i in self.items:  # the old waiting queue is gone: what waited there waits to be seen again
            if i.get("state") in LEGACY_QUEUE:
                i["state"] = "weak"

    def save(self) -> None:
        f = _file(self.vault)
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps({"items": self.items}, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(f)

    def get(self, item_id: str) -> dict | None:
        return next((i for i in self.items if i["id"] == item_id), None)

    def match(self, c: dict) -> dict | None:
        best, score = None, 0.0
        for it in self.items:
            s = similar(c["text"], it["text"])
            same_key = c.get("key") and c["key"].lower() == (it.get("key") or "").lower() and it["where"] == c["where"]
            if same_key and not c.get("contradicts") and 0.6 <= s < 0.85:
                s = 0.85  # same subject, slightly different words
            if (
                c.get("kind") == "rule"
                and it.get("kind") == "rule"
                and not c.get("contradicts")
                and (same_key or same_meaning(c["text"], it["text"]))
            ):
                s = max(s, 0.85)  # a rule said again in other words is the same rule
            if s > score:
                best, score = it, s
        return best if score >= 0.85 else None

    def seen(self, c: dict) -> bool:
        """This very message was already taken into account for this item (read again, not said again)."""
        it = self.match(c) if c.get("ref") else None
        return bool(it and c["ref"] in it["refs"])

    def add(self, c: dict) -> tuple[dict, bool]:
        """Returns (item, is_new). A repeat reinforces the old item instead of creating a new one."""
        it = self.match(c)
        if it and c.get("ref") and c["ref"] in it["refs"]:
            return it, False  # the same message read again is not a repeat
        if it:
            it["count"] += 1
            it["confs"] = (it.get("confs") or [it["confidence"]])[-9:] + [c["confidence"]]
            it["confidence"] = combined(it["confs"])
            it["last_seen"] = now()
            it["refs"] = (it["refs"] + [c["ref"]])[-5:]
            if c.get("evidence"):
                it["evidence"] = (it["evidence"] + [c["evidence"]])[-3:]
            if said_date(c.get("said_at")) and (
                not said_date(it.get("said_at")) or said_date(c["said_at"]) > said_date(it["said_at"])
            ):
                it["said_at"] = c["said_at"]  # the latest time the owner said it
            it["sources"] = sorted(set(it["sources"]) | {c["source"]})
            it["tags"] = sorted(set(it["tags"]) | set(c["tags"]))
            return it, False
        it = {
            "id": secrets.token_hex(4),
            "text": c["text"],
            "kind": c["kind"],
            "where": c["where"],
            "key": c.get("key", ""),
            "tags": c["tags"],
            "confidence": c["confidence"],
            "confs": [c["confidence"]],
            "count": 1,
            "sources": [c["source"]],
            "refs": [c["ref"]],
            "evidence": [c["evidence"]] if c.get("evidence") else [],
            "contradicts": c.get("contradicts", ""),
            "correction": c.get("correction", False),
            "url": c.get("url", ""),
            "said_at": c.get("said_at", ""),
            "first_seen": now(),
            "last_seen": now(),
            "state": "new",
            "event_id": "",
            "decided_by": "",
        }
        self.items.append(it)
        return it, True

    def queue(self) -> list[dict]:
        order = {"conflict": 0, "pending": 1, "forget_pending": 2, "asking": 3}
        return sorted(
            (i for i in self.items if i["state"] in QUEUE_STATES),
            key=lambda i: (order[i["state"]], -i["confidence"], i["last_seen"]),
        )

    def counts(self) -> dict:
        out: dict = {}
        for i in self.items:
            out[i["state"]] = out.get(i["state"], 0) + 1
        return out
