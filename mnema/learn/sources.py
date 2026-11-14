"""Sources: where the owner already lives. Each source turns new material into episodes and remembers
how far it has read (cursor), so nothing is read twice.

An episode is one piece of the owner's own words: a message to an AI, a sent letter, a Telegram
message, new lines in a note. AI replies are kept only as context for corrections ("нет, не так").
"""

from __future__ import annotations

import datetime as dt
import email
import email.policy
import hashlib
import imaplib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..vault import Vault
from ..fsutil import read_json, write_json

BRAIN_MARK = "[MNEMA-EXTRACT]"  # our own extraction prompts — never learn from them


@dataclass
class Episode:
    source: str
    ref: str  # where exactly: file, message id
    ts: str  # ISO time
    text: str  # the owner's words
    prev: str = ""  # what the AI said just before (for corrections)
    title: str = ""  # chat / note / letter subject
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------- cursors


def _cfile(vault: Vault) -> Path:
    return vault.service / "learn" / "cursors.json"


def load_cursors(vault: Vault) -> dict:
    f = _cfile(vault)
    return read_json(f, {}) or {}


def save_cursors(vault: Vault, cur: dict) -> None:
    f = _cfile(vault)
    f.parent.mkdir(parents=True, exist_ok=True)
    write_json(f, cur)


def _since(days: int | None) -> float:
    return 0.0 if not days else (dt.datetime.now() - dt.timedelta(days=days)).timestamp()


def _clip(t: str, n: int) -> str:
    t = t.strip()
    return t if len(t) <= n else t[:n] + "…"


# ---------------------------------------------------------------- Claude Code

MACHINE_TAG = re.compile(r"\[[A-Z][A-Z0-9_-]{2,}\]")  # "[SERVICE] …": a script's prompt, not the owner's words
SKIP_PREFIXES = (
    "<command-",
    "<local-command",
    "<system-reminder",
    "<task-notification",
    "<bash-",
    "Caveat:",
    "This session is being continued",
    BRAIN_MARK,
    "[Request interrupted",
)


def _cc_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text")
    return ""


def read_claude_code(vault: Vault, opts: dict, cursor: dict, days: int | None, limit: int) -> list[Episode]:
    root = Path(str(opts.get("path") or "~/.claude/projects")).expanduser()
    if not root.exists():
        return []
    import tempfile

    own = [(vault.service / "learn" / "brain").resolve(), (Path(tempfile.gettempdir()) / "mnema-brain").resolve()]
    skip_dirs = {re.sub(r"[^A-Za-z0-9]", "-", str(p)) for p in own}  # Claude Code's folder naming
    since = _since(days)
    out: list[Episode] = []
    files = sorted(
        (f for f in root.glob("*/*.jsonl") if f.parent.name not in skip_dirs and f.stat().st_mtime >= since),
        key=lambda f: f.stat().st_mtime,
    )
    for f in files:
        key = str(f)
        done = cursor.get(key, 0)
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        if len(lines) <= done:
            continue
        prev_ai = ""
        for i, line in enumerate(lines):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("isSidechain") or d.get("isMeta"):
                continue
            msg = d.get("message") or {}
            if d.get("type") == "assistant":
                t = _cc_text(msg.get("content"))
                if t.strip():
                    prev_ai = t
                continue
            if d.get("type") != "user" or i < done:
                continue
            text = _cc_text(msg.get("content")).strip()
            if not text or text.startswith(SKIP_PREFIXES) or MACHINE_TAG.match(text) or len(text) < 3:
                continue
            out.append(
                Episode(
                    "claude_code",
                    f"{f.name}#{i}",
                    d.get("timestamp", ""),
                    _clip(text, 3000),
                    prev=_clip(prev_ai, 700),
                    title=f.parent.name,
                )
            )
        cursor[key] = len(lines)
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------- ChatGPT export


def read_chatgpt_export(vault: Vault, opts: dict, cursor: dict, days: int | None, limit: int) -> list[Episode]:
    p = Path(str(opts.get("path") or "")).expanduser()
    if p.is_dir():
        p = p / "conversations.json"
    if not str(opts.get("path") or "") or not p.exists():
        return []
    convs = json.loads(p.read_text(encoding="utf-8"))
    since = _since(days)
    seen = cursor.setdefault("conv", {})
    out = []
    for c in sorted(convs, key=lambda c: c.get("update_time") or 0):
        cid, upd = str(c.get("id") or c.get("conversation_id") or c.get("title")), c.get("update_time") or 0
        if upd < since or seen.get(cid, -1) >= upd:
            continue
        nodes = [n.get("message") for n in (c.get("mapping") or {}).values() if n.get("message")]
        nodes.sort(key=lambda m: m.get("create_time") or 0)
        prev = ""
        last_seen = seen.get(cid, -1)
        for m in nodes:
            role = (m.get("author") or {}).get("role")
            parts = (m.get("content") or {}).get("parts") or []
            text = "\n".join(x for x in parts if isinstance(x, str)).strip()
            if not text:
                continue
            if role == "assistant":
                prev = text
            elif role == "user" and (m.get("create_time") or 0) > last_seen:
                ts = dt.datetime.fromtimestamp(m.get("create_time") or upd).isoformat(timespec="seconds")
                out.append(
                    Episode(
                        "chatgpt_export",
                        f"{cid}#{m.get('id')}",
                        ts,
                        _clip(text, 3000),
                        prev=_clip(prev, 700),
                        title=c.get("title") or "",
                    )
                )
        seen[cid] = upd
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------- notes folder


def read_notes(vault: Vault, opts: dict, cursor: dict, days: int | None, limit: int) -> list[Episode]:
    """Only what's new: lines that weren't in the note last time."""
    root = Path(str(opts.get("path") or "")).expanduser()
    if not str(opts.get("path") or "") or not root.exists():
        return []
    vroot = vault.root.resolve()
    excl = {x.strip() for x in str(opts.get("exclude") or "").split(",") if x.strip()}
    since = _since(days)
    known = cursor.setdefault("files", {})
    out = []
    for f in sorted(root.rglob("*.md"), key=lambda f: f.stat().st_mtime):
        rp = f.resolve()
        if vroot == rp or vroot in rp.parents or any(part in excl for part in f.relative_to(root).parts):
            continue  # never learn from Mnemai's own memory
        st = f.stat()
        key = str(f.relative_to(root))
        prev = known.get(key)
        if st.st_mtime < since or (prev and prev["mtime"] >= st.st_mtime):
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        hashes = [hashlib.md5(l.strip().encode()).hexdigest()[:10] for l in text.splitlines() if l.strip()]
        old = set(prev["lines"]) if prev else set()
        new_lines = [l for l, h in zip([l for l in text.splitlines() if l.strip()], hashes) if h not in old]
        known[key] = {"mtime": st.st_mtime, "lines": hashes}
        body = "\n".join(l for l in new_lines if not l.startswith("---"))
        if len(body.strip()) < 20:
            continue
        out.append(
            Episode(
                "notes",
                key,
                dt.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
                _clip(body, 4000),
                title=f.stem,
            )
        )
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------- mail (sent)

QUOTE_RE = re.compile(
    r"^(On .+wrote:|.+ пишет:|.+ написал\(а\):|-----Original Message-----|-------- Пересылаемое)", re.M
)


def _plain(msg) -> str:
    part = msg.get_body(preferencelist=("plain",)) if hasattr(msg, "get_body") else None
    text = part.get_content() if part else ""
    m = QUOTE_RE.search(text)
    if m:
        text = text[: m.start()]
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith(">")).strip()


def _sent_folder(imap) -> str:
    typ, data = imap.list()
    for raw in data or []:
        line = raw.decode(errors="replace")
        if "\\Sent" in line:
            return line.rsplit(' "/" ', 1)[-1].strip() if ' "/" ' in line else line.split()[-1]
    return "Sent"


def read_mail(vault: Vault, opts: dict, cursor: dict, days: int | None, limit: int, connect=None) -> list[Episode]:
    if not (opts.get("host") and opts.get("user") and opts.get("password")):
        return []
    imap = (connect or (lambda h: imaplib.IMAP4_SSL(h)))(opts["host"])
    try:
        imap.login(opts["user"], opts["password"])
        folder = opts.get("folder") or _sent_folder(imap)
        imap.select(folder if folder.startswith('"') else f'"{folder}"', readonly=True)
        d = days or int(opts.get("days") or 30)
        since = (dt.date.today() - dt.timedelta(days=d)).strftime("%d-%b-%Y")
        last = int(cursor.get("uid", 0))
        typ, data = imap.uid("search", None, f"SINCE {since}")
        uids = [int(u) for u in (data[0] or b"").split() if int(u) > last][:limit]
        out = []
        for uid in uids:
            typ, msgdata = imap.uid("fetch", str(uid), "(RFC822)")
            raw = next((x[1] for x in msgdata if isinstance(x, tuple)), None)
            if not raw:
                continue
            msg = email.message_from_bytes(raw, policy=email.policy.default)
            body = _plain(msg)
            if len(body) >= 20:
                sent = ""
                try:  # «Thu, 21 Sep 2026 13:16:01 +0300» → local ISO; otherwise the fact is dated «today»
                    sent = (
                        email.utils.parsedate_to_datetime(str(msg.get("Date") or ""))
                        .astimezone()
                        .isoformat(timespec="seconds")
                    )
                except (TypeError, ValueError):
                    sent = str(msg.get("Date", "") or "")
                out.append(
                    Episode(
                        "mail",
                        f"uid{uid}",
                        sent,
                        _clip(body, 3000),
                        title=str(msg.get("Subject", "")),
                        meta={"to": str(msg.get("To", ""))[:200]},
                    )
                )
            cursor["uid"] = uid
        return out
    finally:
        try:
            imap.logout()
        except Exception:
            pass


# ---------------------------------------------------------------- Telegram Desktop export


def _tg_text(t) -> str:
    if isinstance(t, str):
        return t
    return " ".join(x if isinstance(x, str) else x.get("text", "") for x in t or [])


def read_telegram(vault: Vault, opts: dict, cursor: dict, days: int | None, limit: int) -> list[Episode]:
    """Telegram Desktop → Settings → Export chat history → JSON. Only the owner's own messages,
    one episode per chat per day."""
    p = Path(str(opts.get("path") or "")).expanduser()
    if p.is_dir():
        p = p / "result.json"
    if not str(opts.get("path") or "") or not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    me = (data.get("personal_information") or {}).get("user_id")
    chats = (data.get("chats") or {}).get("list") or ([data] if "messages" in data else [])
    since = dt.datetime.fromtimestamp(_since(days)) if days else None
    done = cursor.setdefault("chats", {})
    out = []
    for ch in chats:
        cid = str(ch.get("id") or ch.get("name"))
        last = done.get(cid, "")
        days_map: dict[str, list[str]] = {}
        newest = last
        for m in ch.get("messages") or []:
            if m.get("type") != "message":
                continue
            mine = (me and m.get("from_id") == f"user{me}") or (not me and m.get("from") == opts.get("me_name"))
            date = m.get("date", "")
            if not mine or date <= last or (since and date < since.isoformat()):
                continue
            text = _tg_text(m.get("text")).strip()
            if text:
                days_map.setdefault(date[:10], []).append(text)
            newest = max(newest, date)
        for day, msgs in sorted(days_map.items()):
            out.append(
                Episode("telegram", f"{cid}@{day}", day, _clip("\n".join(msgs), 3000), title=ch.get("name") or "")
            )
        done[cid] = newest
        if len(out) >= limit:
            break
    return out


def _life(name):
    def call(*a, **k):
        from . import sources_life

        return getattr(sources_life, name)(*a, **k)

    return call


READERS = {
    "claude_code": read_claude_code,
    "chatgpt_export": read_chatgpt_export,
    "notes": read_notes,
    "mail": read_mail,
    "telegram": read_telegram,
    "telegram_api": lambda *a, **k: __import__("mnema.learn.tg_api", fromlist=["read"]).read(*a, **k),
    "calendar": _life("read_calendar"),
    "documents": _life("read_documents"),
    "browser_history": _life("read_browser_history"),
}
