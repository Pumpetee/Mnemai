"""Vault: the memory itself — a folder of plain Markdown files the owner can read and edit.

Layout — numbered folders, the same logic as a well-kept second brain
-----------------------------------------------------------------------
00 Inbox/Inbox.md                facts not yet sorted (scope: inbox)
10 Now.md                        generated "today" layer — never edit by hand
20 Projects/<name>/_Project.md   project hub: status, goal, started, keywords (scope: projects); its documents beside it
30 People/<name>.md              one card per person (scope: people)
60 Events/YYYY-MM.md             dated events and decisions, newest first (scope: decisions)
70 Memory/Profile.md             who I am (scope: profile)
70 Memory/Rules.md               how to work with me: one rule per line, with date (scope: rules)
70 Memory/Thoughts.md            the owner's ideas, one line each (scope: notes)
70 Memory/Cards/<topic>.md       one card per topic: one fact per line, keywords in the header (scope: cards)
70 Memory/Fact archive/          facts replaced by newer ones — history, not context
70 Memory/Index.md               generated: every card, project and person with its keywords
80 Meetings/                     meeting transcripts and summaries
90 System/Journal/YYYY-MM-DD.md  what was written, by whom, in plain words
90 System/Recipes/               recipes of repeated tasks (prompts)
95 Saves/                        copy of a file before it changes, two latest versions
99 Archive/                      closed projects and old cards
.mnema/                          service files: clients.json, journal.jsonl, snapshots/, token

Any heading may carry tags: "## Деньги #money". Tagged sections can be hidden from
specific assistants (see clients.py). A whole note can be tagged with `tags: [health]`.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path

SERVICE_DIR = ".mnema"
INBOX = "00 Inbox/Inbox.md"
NOW = "10 Now.md"
PROJECTS = "20 Projects"
PROJECT_HUB = "_Project.md"
PEOPLE = "30 People"
EVENTS = "60 Events"
MEMORY = "70 Memory"
PROFILE = "70 Memory/Profile.md"
RULES = "70 Memory/Rules.md"
THOUGHTS = "70 Memory/Thoughts.md"
CARDS = "70 Memory/Cards"
FACT_ARCHIVE = "70 Memory/Fact archive"
INDEX = "70 Memory/Index.md"
MEETINGS = "80 Meetings"
SYSTEM = "90 System"
JOURNAL = "90 System/Journal"
PROMPTS = "90 System/Recipes"  # «рецепты задач»; before 0.5.3 — 90 System/Prompts
OLD_PROMPTS = "90 System/Prompts"
SAVES = "95 Saves"
ARCHIVE = "99 Archive"
FOLDERS = [
    "00 Inbox",
    PROJECTS,
    PEOPLE,
    EVENTS,
    MEMORY,
    CARDS,
    FACT_ARCHIVE,
    MEETINGS,
    JOURNAL,
    PROMPTS,
    SAVES,
    ARCHIVE,
]
TOP_FILES = {INBOX: "inbox", PROFILE: "profile", RULES: "rules", THOUGHTS: "notes"}
GENERATED = {NOW, INDEX}
# history and copies: kept for the owner, never fed to an assistant or searched as memory
NOT_MEMORY = (FACT_ARCHIVE + "/", SYSTEM + "/", SAVES + "/", ARCHIVE + "/")

TAG_RE = re.compile(r"(?<!\w)#([\w-]+)", re.UNICODE)
# the hidden topics in the owner's own words: «#деньги» hides like «#money», whatever the case
TAG_ALIASES = {
    "деньги": "money",
    "финансы": "money",
    "здоровье": "health",
    "личное": "private",
    "приватное": "private",
    "личный": "private",
}


def norm_tag(tag) -> str:
    """ "#Money", "money", "#деньги" → "money": tags compare in one form everywhere."""
    t = str(tag).strip().strip("\"'").lstrip("#").strip().lower()
    return TAG_ALIASES.get(t, t)


def tags_of(value) -> set:
    """Tags from a frontmatter value or a line of text: a list, "a, b", "[a, b]" or "#a #b"."""
    if value is None or value == "":
        return set()
    items = value if isinstance(value, (list, tuple, set)) else re.split(r"[,\s]+", str(value).strip("[]"))
    return {norm_tag(x) for x in items if norm_tag(x)}


def line_tags(line: str) -> set:
    return {norm_tag(t) for t in TAG_RE.findall(line or "")}


STATUS_RE = re.compile(r"\((?:статус|status)\s+(\d{1,2})\.(\d{1,2})\.(\d{4})\)", re.IGNORECASE)
ISO_STATUS_RE = re.compile(r"\((?:статус|status)\s+(\d{4})-(\d{2})-(\d{2})\)", re.IGNORECASE)


# ---------------------------------------------------------------- frontmatter

PROP_RE = re.compile(r"^\s*(?:[\w-]+\s*:|-\s)")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """A YAML subset: `key: value`, `key: [a, b]` and the list form Obsidian writes (`key:` then `  - a` lines).
    A header without its closing `---` is read up to the first line that is not a property."""
    text = text.replace("\r\n", "\n")
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:  # not closed: the properties end where a heading, a blank line or plain text starts
        lines = text[3:].lstrip("\n").split("\n")
        k = 0
        while k < len(lines) and PROP_RE.match(lines[k]) and not lines[k].startswith("#"):
            k += 1
        head, body = "\n".join(lines[:k]), "\n".join(lines[k:])
    else:
        head, body = text[3:end], text[end + 4 :]
    meta: dict = {}
    last = None
    for line in head.strip("\n").splitlines():
        if line.lstrip().startswith("#") or not line.strip():
            continue
        item = re.match(r"^\s*-\s(.*)$", line)  # one space after the dash, the rest is stripped below
        if item and last is not None:  # Obsidian's list form
            cur = meta.get(last)
            meta[last] = (cur if isinstance(cur, list) else []) + [item.group(1).strip().strip("\"'")]
            continue
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key, val = key.strip(), val.strip()
        last = key
        if val.startswith("[") or val.endswith("]"):
            meta[key] = [v.strip().strip("\"'") for v in val.strip("[]").split(",") if v.strip()]
        else:
            meta[key] = val.strip("\"'")
    return meta, body.lstrip("\n")


def dump_frontmatter(meta: dict, body: str) -> str:
    if not meta:
        return body
    lines = ["---"]
    for k, v in meta.items():
        if isinstance(v, (list, tuple)):
            lines.append(f"{k}: [{', '.join(str(x) for x in v)}]")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body.lstrip("\n")


# ---------------------------------------------------------------- notes


@dataclass
class Section:
    heading: str  # "" for the text before the first heading
    level: int
    text: str  # heading line included
    tags: set = field(default_factory=set)


@dataclass
class Note:
    rel: str  # path relative to the vault, forward slashes
    meta: dict
    body: str

    @property
    def scope(self) -> str:
        if self.meta.get("scope"):
            return str(self.meta["scope"])
        if self.rel in TOP_FILES:
            return TOP_FILES[self.rel]
        parts = self.rel.split("/")
        if parts[0] == PROJECTS:
            return "projects" if len(parts) == 3 and parts[2] == PROJECT_HUB else "notes"
        if parts[0] == PEOPLE and len(parts) == 2:
            return "people"
        if parts[0] == EVENTS:
            return "decisions"
        if self.rel.startswith(CARDS + "/"):
            return "cards"
        if parts[0] == MEETINGS:
            return "meetings"
        return "notes"

    @property
    def title(self) -> str:
        if self.meta.get("title"):
            return str(self.meta["title"])
        for line in self.body.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        parts = self.rel.split("/")
        return parts[-2] if parts[-1] == PROJECT_HUB and len(parts) > 1 else parts[-1][:-3]

    @property
    def keywords(self) -> list:
        k = self.meta.get("keywords", [])
        return k if isinstance(k, list) else [k]

    @property
    def tags(self) -> set:
        """Frontmatter tags and the ones on the «# Title» line: both hide the whole note."""
        title = next((l for l in self.body.splitlines() if l.startswith("# ")), "")
        return tags_of(self.meta.get("tags")) | tags_of(self.meta.get("tag")) | line_tags(title)

    def sections(self) -> list[Section]:
        out, cur, level, heading = [], [], 0, ""
        for line in self.body.splitlines(keepends=True):
            m = re.match(r"^(#{2,6})\s+(.*)", line)
            if m:
                if cur:
                    out.append(Section(heading, level, "".join(cur), line_tags(heading)))
                heading, level, cur = m.group(2).strip(), len(m.group(1)), [line]
            else:
                cur.append(line)
        if cur:
            out.append(Section(heading, level, "".join(cur), line_tags(heading)))
        # nested sections inherit tags of their parent
        stack: list[Section] = []
        for s in out:
            while stack and stack[-1].level >= s.level and s.level:
                stack.pop()
            for p in stack:
                s.tags |= p.tags
            if s.level:
                stack.append(s)
        return out

    def visible_text(self, deny_tags: set) -> str:
        """Body without sections whose tags intersect deny_tags."""
        deny_tags = {norm_tag(t) for t in deny_tags or ()}
        if self.tags & deny_tags:
            return ""
        return "".join(s.text for s in self.sections() if not (s.tags & deny_tags))


# ---------------------------------------------------------------- dates and staleness


def parse_date(value: str) -> dt.date | None:
    value = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return dt.datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def status_dates(line: str) -> list[dt.date]:
    out = []
    for d, m, y in STATUS_RE.findall(line):
        try:
            out.append(dt.date(int(y), int(m), int(d)))
        except ValueError:
            pass
    for y, m, d in ISO_STATUS_RE.findall(line):
        try:
            out.append(dt.date(int(y), int(m), int(d)))
        except ValueError:
            pass
    return out


@dataclass
class StaleFact:
    rel: str
    text: str
    date: dt.date
    age_days: int
    tags: set = field(default_factory=set)  # note tags + section tags — used to hide private facts


# ---------------------------------------------------------------- vault


def read_text(p: Path) -> str:
    """A note as text. Notepad's «ANSI» (Windows-1251) and a BOM are read too: one such file must not stop memory."""
    data = p.read_bytes()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp1251", errors="replace")
    return text.replace("\r\n", "\n").replace("\r", "\n")  # as text mode reads it


class Vault:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        if (self.root / SERVICE_DIR / "crypto.json").exists():  # encrypted by Mnemai: its key, if it is here
            from . import crypt

            crypt.attach(self.root)

    def lock(self):
        from .locks import vault_lock

        return vault_lock(self.root)

    # -- paths
    @property
    def service(self) -> Path:
        return self.root / SERVICE_DIR

    def path(self, rel: str) -> Path:
        p = (self.root / rel).resolve()
        if self.root not in p.parents and p != self.root:
            raise ValueError(f"path escapes the vault: {rel}")
        return p

    def exists(self) -> bool:
        return (self.root / PROFILE).exists()

    # -- reading
    def notes(self) -> list[Note]:
        out = []
        for p in sorted(self.root.rglob("*.md")):
            rel = p.relative_to(self.root).as_posix()
            if (
                rel.startswith(SERVICE_DIR)
                or rel in GENERATED
                or rel.startswith(NOT_MEMORY)
                or any(part.startswith(".") for part in p.relative_to(self.root).parts)
            ):
                continue
            try:
                out.append(self.read(rel))
            except OSError:  # gone or locked meanwhile: the next read sees it
                continue
        return out

    def read(self, rel: str) -> Note:
        text = read_text(self.path(rel))
        meta, body = parse_frontmatter(text)
        return Note(rel, meta, body)

    def read_raw(self, rel: str) -> str | None:
        p = self.path(rel)
        return read_text(p) if p.exists() else None

    def write_raw(self, rel: str, text: str) -> None:
        """Written next to the file and swapped in: a full disk or a killed process never leaves half a note."""
        import os
        import threading
        import time

        p = self.path(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(f"{p.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        try:
            from .fsutil import _crypt_on

            if _crypt_on():  # an encrypted memory folder: the note goes to disk encrypted
                from . import crypt

                with open(tmp, "wb") as fh:
                    fh.write(crypt.text_for(p, text))
            else:
                with open(tmp, "w", encoding="utf-8") as fh:
                    fh.write(text)
            for _ in range(20):
                try:
                    os.replace(tmp, p)
                    return
                except PermissionError:  # Windows: a reader holds the file for a moment
                    time.sleep(0.05)
            os.replace(tmp, p)
        except BaseException:
            try:
                tmp.unlink()
            except OSError:
                pass
            raise

    def delete(self, rel: str) -> None:
        p = self.path(rel)
        if p.exists():
            p.unlink()

    # -- queries
    def by_scope(self, scope: str) -> list[Note]:
        return [n for n in self.notes() if n.scope == scope]

    def find_note(self, scope: str, name: str) -> Note | None:
        def flat(s: str) -> str:
            return re.sub(r"\s+", " ", s).strip().lower()

        key = flat(name)
        for n in self.by_scope(scope):
            parts = n.rel.split("/")
            stem = parts[-2] if parts[-1] == PROJECT_HUB else parts[-1][:-3]
            if n.title.lower() == key or stem.lower() == key or flat(n.title) == key or flat(stem) == key:
                return n
        return None

    def stale(self, today: dt.date | None = None, max_age_days: int = 30) -> list[StaleFact]:
        today = today or dt.date.today()
        out = []
        for n in self.notes():
            if n.scope in ("decisions", "meetings"):  # history: dated on purpose, nothing to re-check
                continue
            upd = parse_date(str(n.meta.get("updated", "")))
            if upd and n.scope == "projects" and str(n.meta.get("status", "active")) == "active":
                age = (today - upd).days
                if age > max_age_days:
                    out.append(StaleFact(n.rel, f"{n.title}: проект не обновлялся", upd, age, set(n.tags)))
            for sec in n.sections():
                for line in sec.text.splitlines():
                    for d in status_dates(line):
                        age = (today - d).days
                        if age > max_age_days:
                            out.append(StaleFact(n.rel, line.strip(" -*"), d, age, set(n.tags) | sec.tags))
        return sorted(out, key=lambda s: -s.age_days)

    def search(
        self, query: str, scopes: set | None = None, deny_tags: set | None = None, limit: int = 20
    ) -> list[tuple[str, str]]:
        words = [w for w in re.findall(r"\w+", query.lower()) if len(w) > 1]
        if not words:
            return []
        hits = []
        for n in self.notes():
            if scopes is not None and n.scope not in scopes:
                continue
            text = n.visible_text(deny_tags or set())
            for line in text.splitlines():
                low = line.lower()
                score = sum(1 for w in words if w in low or (len(w) > 4 and w[:-1] in low))
                if score:
                    hits.append((score, n.rel, line.strip()))
        hits.sort(key=lambda h: -h[0])
        return [(rel, line) for _, rel, line in hits[:limit]]
