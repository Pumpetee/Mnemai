"""Journal: every read and write by every assistant, with undo for writes.

Events are JSON lines in <vault>/.mnema/journal.jsonl. A write keeps a snapshot of the file
before the change, so it can be rolled back — but only if nobody changed the file after it.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import time
import uuid

from .vault import Vault


def _jfile(vault: Vault):
    return vault.service / "journal.jsonl"


def _sdir(vault: Vault):
    return vault.service / "snapshots"


def _hash(text: str | None) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16] if text is not None else "absent"


def log_event(
    vault: Vault, client: str, action: str, summary: str, paths: list[str] | None = None, extra: dict | None = None
) -> dict:
    ev = {
        "id": uuid.uuid4().hex[:10],
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "client": client,
        "action": action,
        "summary": summary,
        "paths": paths or [],
    }
    if extra:
        ev.update(extra)
    f = _jfile(vault)
    f.parent.mkdir(parents=True, exist_ok=True)
    from .fsutil import append_text

    append_text(f, json.dumps(ev, ensure_ascii=False) + "\n")
    rotate(vault)
    return ev


JOURNAL_ROTATE_MB = 10
JOURNAL_ROTATE_KEEP = 5


def rotate(vault: Vault, mb: int | None = None, keep: int | None = None) -> dict | None:
    """Rotate journal.jsonl: over `mb` megabytes it is archived with the date; the latest `keep` archives stay.

    The owner's decision (20.11.2026): the threshold is 10 MB and 5 archives are kept. An archived file keeps
    its encrypted form, like the journal itself.
    """
    mb = JOURNAL_ROTATE_MB if mb is None else mb
    keep = JOURNAL_ROTATE_KEEP if keep is None else keep
    f = _jfile(vault)
    try:
        size = f.stat().st_size
    except OSError:
        return None
    if size <= mb * 1024 * 1024:
        return None
    arc = f.parent / f"journal-{time.strftime('%Y-%m-%d')}.jsonl"
    i = 1
    while arc.exists():  # a second rotation on the same day: keep both, the older one is dropped by the limit
        i += 1
        arc = f.parent / f"journal-{time.strftime('%Y-%m-%d')}-{i}.jsonl"
    f.rename(arc)
    olds = sorted(f.parent.glob("journal-*.jsonl"))
    for old in olds[:-keep]:
        old.unlink(missing_ok=True)
    return {"archived": arc.name, "kept": min(len(olds), keep)}


SAVES_KEEP = 2


def save_copy(vault: Vault, rel: str, before: str | None) -> str | None:
    """«95 Saves»: a copy of the file as it was before the first change of the day, the two latest versions kept."""
    from .vault import GENERATED, SAVES, SYSTEM

    if before is None or rel in GENERATED or rel.startswith((SAVES + "/", SYSTEM + "/")):
        return None
    stem = rel[:-3] if rel.endswith(".md") else rel
    day = time.strftime("%Y-%m-%d")
    target = vault.root / SAVES / f"{stem}_{day}.md"
    if target.exists():
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(before, encoding="utf-8")
    olds = sorted(target.parent.glob(f"{target.name.rsplit('_', 1)[0]}_????-??-??.md"))
    for old in olds[:-SAVES_KEEP]:
        old.unlink(missing_ok=True)
    return target.relative_to(vault.root).as_posix()


WHO = {"owner": "Ты", "learner": "Обучение"}


def journal_line(vault: Vault, client: str, rel: str, summary: str) -> None:
    """«90 System/Journal/<day>.md»: what was written, by whom, in plain words."""
    from .vault import JOURNAL

    who = WHO.get(client)
    if not who:
        try:
            from .clients import get_client

            who = get_client(vault, client).name
        except Exception:
            who = client
    f = vault.root / JOURNAL / f"{time.strftime('%Y-%m-%d')}.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    head = (
        ""
        if f.exists()
        else f"# Журнал — {time.strftime('%d.%m.%Y')}\n\nЧто записано в память и кем. Откатить — в Mnemai, «История».\n\n"
    )
    from .fsutil import append_text

    append_text(f, f"{head}- {time.strftime('%H:%M')} · {who} · {rel} — {summary}\n")


def write_with_journal(vault: Vault, client: str, rel: str, new_text: str, summary: str) -> dict:
    """Write a file and journal it with a snapshot of the previous content."""
    with vault.lock():
        return _write_with_journal(vault, client, rel, new_text, summary)


def _write_with_journal(vault: Vault, client: str, rel: str, new_text: str, summary: str) -> dict:
    before = vault.read_raw(rel)
    save_copy(vault, rel, before)
    vault.write_raw(rel, new_text)
    ev = log_event(vault, client, "write", summary, [rel], {"after": _hash(new_text)})
    try:
        journal_line(vault, client, rel, summary)
    except OSError:
        pass
    sd = _sdir(vault)
    sd.mkdir(parents=True, exist_ok=True)
    (sd / f"{ev['id']}.json").write_text(
        json.dumps({"rel": rel, "before": before, "after": new_text}, ensure_ascii=False), encoding="utf-8"
    )
    return ev


def events(vault: Vault, limit: int = 100) -> list[dict]:
    f = _jfile(vault)
    if not f.exists():
        return []
    lines = f.read_text(encoding="utf-8").splitlines()
    out = []
    for line in reversed(lines):
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if len(out) >= limit:
            break
    return out


class UndoError(Exception):
    pass


def _undo_file(vault: Vault, ev: dict, data: dict, client: str) -> dict:
    import base64
    import os
    from pathlib import Path

    p = Path(data["rel"])
    cur = p.read_bytes() if p.exists() else None
    if cur is None or hashlib.sha256(cur).hexdigest()[:16] != ev.get("after"):
        raise UndoError(f"файл {p} менялся после этого действия — откат вручную")
    if data.get("before_b64") is None:
        p.unlink()
    else:
        tmp = p.with_name(p.name + ".undo.tmp")
        tmp.write_bytes(base64.b64decode(data["before_b64"]))
        os.replace(tmp, p)
    return log_event(vault, client, "undo", f"откат: {ev['summary']}", [str(p)], {"undoes": ev["id"]})


META_LINE = re.compile(r"^(updated|status_updated):")


def _undo_lines(before: str | None, after: str | None, current: str | None) -> str | None:
    """What this write changed (lines added or replaced) put back in the current file, other later changes kept.
    None if it cannot be done safely: no record of the write, a line it added is gone, or it deleted lines."""
    if after is None or current is None:
        return None
    if before is None:
        # the very first write into a new file: take back only the lines it added, later lines stay
        added = [l for l in after.split("\n") if l.strip()]
        cur = current.split("\n")
        pos = next((k for k in range(len(cur) - len(added) + 1) if cur[k : k + len(added)] == added), -1)
        if pos < 0:
            return None
        cur[pos : pos + len(added)] = []
        return "\n".join(cur)
    b, a, cur = before.split("\n"), after.split("\n"), current.split("\n")
    for tag, i1, i2, j1, j2 in reversed(difflib.SequenceMatcher(None, b, a, autojunk=False).get_opcodes()):
        if tag == "equal":
            continue
        new, old = a[j1:j2], b[i1:i2]
        if all(META_LINE.match(x) for x in new + old):
            continue  # the date in the header: later writes moved it on anyway
        if tag == "delete" or not new:
            return None
        at = next((k for k in range(len(cur) - len(new) + 1) if cur[k : k + len(new)] == new), -1)
        if at < 0:
            return None
        cur[at : at + len(new)] = old
    return "\n".join(cur)


def undo(vault: Vault, event_id: str, client: str = "owner") -> dict:
    with vault.lock():
        return _undo(vault, event_id, client)


def _undo(vault: Vault, event_id: str, client: str = "owner") -> dict:
    ev = next((e for e in events(vault, 100000) if e["id"] == event_id), None)
    if not ev:
        raise UndoError(f"событие {event_id} не найдено")
    if ev["action"] != "write":
        raise UndoError("откатить можно только запись")
    if any(e.get("undoes") == event_id for e in events(vault, 100000)):
        raise UndoError("эта запись уже откачена")
    snap = _sdir(vault) / f"{event_id}.json"
    if not snap.exists():
        raise UndoError("нет снимка для отката")
    data = json.loads(snap.read_text(encoding="utf-8"))
    if data.get("abs"):  # a file outside the memory folder, written by an action in the chat
        return _undo_file(vault, ev, data, client)
    rel, before = data["rel"], data["before"]
    current = vault.read_raw(rel)
    if _hash(current) != ev.get("after"):
        # the file changed later (learning writes the same files often): take back only this write's own lines
        undone = _undo_lines(before, data.get("after"), current)
        if undone is None:
            raise UndoError(f"файл {rel} менялся после этой записи, а её строк в нём уже нет — откат вручную")
        vault.write_raw(rel, undone)
        return log_event(vault, client, "undo", f"откат: {ev['summary']}", [rel], {"undoes": event_id})
    if before is None:
        vault.delete(rel)
    else:
        vault.write_raw(rel, before)
    return log_event(vault, client, "undo", f"откат: {ev['summary']}", [rel], {"undoes": event_id})
