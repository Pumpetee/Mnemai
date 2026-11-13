"""High-level memory operations: create a vault, remember facts, build context for an assistant.

The logic of a well-kept second brain:
- one fact per line, with its date; a status fact carries "(статус ДД.ММ.ГГГГ)";
- a status that changed is replaced, not piled up: the old line goes to «70 Memory/Fact archive»;
- every topic has its card with keywords in the header, the generated Index lists them all;
- a project is a folder with a hub (_Project.md): status, goal, start date; closed projects move to «99 Archive»;
- decisions and status changes go to the event feed «60 Events», what was written — to the journal;
- «10 Now.md» and «70 Memory/Index.md» are generated: edit the sources, not them;
- statuses older than 30 days are asked about, not trusted silently.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
import secrets
import shutil

from .clients import Client, get_client, save_clients, DEFAULT_CLIENTS
from .journal import log_event, write_with_journal
from .locks import locked
from .vault import (
    ARCHIVE,
    CARDS,
    EVENTS,
    FACT_ARCHIVE,
    FOLDERS,
    INBOX,
    INDEX,
    NOW,
    PEOPLE,
    PROFILE,
    PROJECT_HUB,
    PROJECTS,
    RULES,
    THOUGHTS,
    Vault,
    dump_frontmatter,
    line_tags,
    norm_tag,
    tags_of,
    parse_frontmatter,
    status_dates,
)

CHUNK_LIMIT = 9000  # Claude Code keeps max 10 000 chars from one hook; leave room for a header
FRESH_DAYS = 14
STALE_DAYS = 30

TEMPLATES = {
    PROFILE: """---
updated: {today}
---

# Обо мне

Кто я в двух-трёх фразах: чем занимаюсь, где живу, что сейчас главное.

## Как со мной говорить

- Стиль: коротко и по делу.
""",
    RULES: """---
updated: {today}
---

# Правила

> Одно правило — одна строка с датой. Новое дописывается, изменившееся заменяется, а не дублируется.

- Не выдумывай факты: если не знаешь — скажи.
""",
    INBOX: """# Входящие

Факты, которые ещё не разложены по карточкам.
""",
    THOUGHTS: """# Мысли

Идеи владельца, одна строка — одна мысль.
""",
}
GEN_NOTE = "> Собирается автоматически. Править не нужно: правьте исходные заметки."
CLOSED = {"closed", "archive", "done", "cancelled", "закрыт", "закрыто", "завершён", "завершен", "архив", "отменён"}
STATUS_WORDS = {
    "active": "active",
    "активен": "active",
    "в работе": "active",
    "paused": "paused",
    "пауза": "paused",
    "на паузе": "paused",
    **{w: "closed" for w in CLOSED},
}
TAG_TITLES = {"money": "Деньги", "health": "Здоровье", "private": "Личное"}


def today_str(today: dt.date | None = None) -> str:
    return (today or dt.date.today()).strftime("%Y-%m-%d")


def ru_date(today: dt.date | None = None) -> str:
    return (today or dt.date.today()).strftime("%d.%m.%Y")


# ---------------------------------------------------------------- init


def init_vault(vault: Vault) -> list[str]:
    created = []
    vault.root.mkdir(parents=True, exist_ok=True)
    for rel, tpl in TEMPLATES.items():
        if vault.read_raw(rel) is None:
            vault.write_raw(rel, tpl.format(today=today_str()))
            created.append(rel)
    for d in FOLDERS:
        (vault.root / d).mkdir(parents=True, exist_ok=True)
    vault.service.mkdir(exist_ok=True)
    if not (vault.service / "clients.json").exists():
        save_clients(vault, {c.id: c for c in DEFAULT_CLIENTS})
    if not (vault.service / "token").exists():
        (vault.service / "token").write_text(secrets.token_urlsafe(24), encoding="utf-8")
    generate_now(vault)
    return created


def token(vault: Vault, kind: str = "token") -> str:
    """kind="token" — full access for the local app."""
    f = vault.service / kind
    if not f.exists():
        vault.service.mkdir(parents=True, exist_ok=True)
        f.write_text(secrets.token_urlsafe(24), encoding="utf-8")
    return f.read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------- lines and keys


class PermissionDenied(Exception):
    pass


def _slug(name: str) -> str:
    s = re.sub(r"[\\/:*?\"<>|#]+", " ", name).strip()
    return re.sub(r"\s+", " ", s)[:80].strip(" .") or "без названия"


def _split_tags(name: str) -> tuple[str, list[str]]:
    """ "Деньги #money" → ("Деньги", ["money"])."""
    tags = list(dict.fromkeys(norm_tag(t) for t in re.findall(r"#([\w-]+)", name)))
    return re.sub(r"(?:^|\s)#[\w-]+", "", name).strip(), tags


def _append_section(body: str, heading: str, line: str) -> str:
    """Append a line under '## heading', creating the section at the end if needed."""
    lines = body.rstrip("\n").splitlines()
    idx = next((i for i, l in enumerate(lines) if l.strip() == f"## {heading}"), None)
    if idx is None:
        return "\n".join(lines) + f"\n\n## {heading}\n\n{line}\n"
    end = next((j for j in range(idx + 1, len(lines)) if lines[j].startswith("## ")), len(lines))
    while end > idx + 1 and not lines[end - 1].strip():
        end -= 1
    lines.insert(end, line)
    return "\n".join(lines) + "\n"


def fact_key(line: str) -> str:
    """What a fact is about: the words before the first dash or colon, without dates and markup.
    "- **Пилот (статус 01.10.2026):** две компании" → "пилот"."""
    t = re.sub(r"^\s*[-*]\s+", "", line)
    t = re.sub(
        r"\((?:статус|status)[^()]*\)|\(\d{1,2}\.\d{1,2}\.\d{4}\)|\d{1,2}\.\d{1,2}\.\d{4}\s*·?", " ", t, flags=re.I
    )
    t = t.replace("**", "").replace("__", "")
    m = re.search(r"\s[—–-]\s|:\s", t)
    head = t[: m.start()] if m and m.start() <= 70 else ""
    return " ".join(re.sub(r"[^\w\s]", " ", head.lower()).split())


def _same_status(old: str, new: str) -> bool:
    """Two status facts about the same thing: the newer one replaces the older one."""
    if not status_dates(old):
        return False
    ko, kn = fact_key(old), fact_key(new)
    if ko and kn and len(kn) >= 3 and ko == kn:
        return True
    from .learn.ledger import similar

    return similar(old, new) >= 0.6


@locked
def _archive_lines(vault: Vault, rel: str, lines: list[str], why: str, today: dt.date | None = None) -> None:
    """Replaced or outdated facts are history: kept in «Fact archive», never fed to assistants."""
    if not lines:
        return
    parts = rel.split("/")
    name = parts[-2] if parts[-1] == PROJECT_HUB else parts[-1][:-3]
    arel = f"{FACT_ARCHIVE}/{name}.md"
    text = (
        vault.read_raw(arel)
        or f"# {name} — архив фактов\n\nСтарые версии фактов из «{rel}». Ассистентам не показываются.\n"
    )
    add = "".join(f"- {l.strip().lstrip('-* ').strip()} → {why} {ru_date(today)}\n" for l in lines)
    vault.write_raw(arel, text.rstrip("\n") + "\n" + add)


def _put_fact(body: str, line: str, heading: str | None = None) -> tuple[str, list[str]]:
    """Add a fact line; a status fact replaces the older status of the same thing. Returns (body, replaced lines)."""
    lines = body.rstrip("\n").splitlines()
    if status_dates(line):
        for i, old in enumerate(lines):
            if old.lstrip().startswith(("-", "*")) and _same_status(old, line):
                lines[i] = line
                return "\n".join(lines) + "\n", [old]
    if heading:
        return _append_section(body, heading, line), []
    return "\n".join(lines) + "\n" + line + "\n", []


# ---------------------------------------------------------------- events


def _event_text(vault: Vault, text: str, d: dt.date, label: str = "") -> tuple[str, str]:
    rel = f"{EVENTS}/{d:%Y-%m}.md"
    raw = vault.read_raw(rel) or f"# События — {d:%m.%Y}\n\nРешения, смены статусов и заметные события, новые сверху.\n"
    meta, body = parse_frontmatter(raw)
    lines = body.splitlines()
    first = next((i for i, l in enumerate(lines) if l.startswith("- ")), len(lines))
    lines.insert(first, f"- {ru_date(d)} · {label + ' — ' if label else ''}{text}")
    return rel, dump_frontmatter(meta, "\n".join(lines) + "\n")


@locked
def add_event(vault: Vault, text: str, today: dt.date | None = None, label: str = "") -> str:
    """One dated line in the event feed of the month, newest first."""
    rel, new = _event_text(vault, text, today or dt.date.today(), label)
    vault.write_raw(rel, new)
    return rel


def hidden_titles(vault: Vault, deny: set) -> list[str]:
    """Titles of whole notes hidden from this assistant: older event lines that start with one ("Деньги: …") are its."""
    if not deny:
        return []
    return [n.title.lower() for n in vault.notes() if n.tags & deny and n.scope in ("cards", "projects", "people")]


def event_hidden(line: str, deny: set, titles: list[str]) -> bool:
    if not deny:
        return False
    if line_tags(line) & deny:
        return True
    text = line.split(" · ", 1)[-1].lower()
    text = re.sub(r"^(решение|decision)\s+—\s+", "", text)
    return any(text.startswith(t + ":") or f"«{t}»" in text for t in titles)


def events(vault: Vault, limit: int = 20) -> list[str]:
    out = []
    for n in sorted(vault.by_scope("decisions"), key=lambda n: n.rel, reverse=True):
        out += [l for l in n.body.splitlines() if l.startswith("- ")]
        if len(out) >= limit:
            break
    return out[:limit]


# ---------------------------------------------------------------- projects


def project_rel(name: str) -> str:
    return f"{PROJECTS}/{_slug(name)}/{PROJECT_HUB}"


def _new_project(name: str, today: dt.date | None) -> tuple[dict, str]:
    meta = {
        "type": "project",
        "status": "active",
        "goal": "",
        "started": today_str(today),
        "updated": today_str(today),
        "keywords": [w for w in re.findall(r"\w{3,}", name.lower())][:6],
    }
    return meta, f"# {name.strip()}\n\n## Журнал\n"


@locked
def set_project_status(
    vault: Vault, name: str, status: str, client_id: str = "owner", today: dt.date | None = None
) -> dict:
    """active | paused | closed. A closed project moves to «99 Archive/Projects» with its documents."""
    status = STATUS_WORDS.get(status.strip().lower(), status.strip().lower())
    note = vault.find_note("projects", name)
    if not note:
        raise KeyError(f"нет проекта «{name}»")
    meta = dict(note.meta)
    old = str(meta.get("status", "active"))
    meta.update(status=status, updated=today_str(today), status_updated=today_str(today))
    ev = write_with_journal(
        vault, client_id, note.rel, dump_frontmatter(meta, note.body), f"проект {note.title}: статус {status}"
    )
    if old != status:
        add_event(vault, f"проект «{note.title}»: {old} → {status}", today)
    if status in ("closed",):
        src = vault.path(note.rel).parent
        dst = vault.root / ARCHIVE / "Projects" / src.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            dst = dst.with_name(f"{src.name} {today_str(today)}")
        shutil.move(str(src), str(dst))
        log_event(
            vault,
            client_id,
            "write",
            f"проект «{note.title}» перенесён в архив",
            [dst.relative_to(vault.root).as_posix()],
        )
    generate_now(vault, today)
    return ev


# ---------------------------------------------------------------- remember

PLACES = {
    "inbox": "inbox",
    "decisions": "decisions",
    "rules": "rules",
    "project": "projects",
    "person": "people",
    "profile": "profile",
    "card": "cards",
    "thought": "notes",
}


@locked
def remember(
    vault: Vault,
    fact: str,
    where: str = "inbox",
    client_id: str = "owner",
    today: dt.date | None = None,
    said: dt.date | None = None,
) -> dict:
    """Save a fact. where: inbox | decisions | rules | thought | world | card:<topic> | project:<name> | person:<name> |
    profile:<heading>.

    said — the day the owner actually said it (learning from old chats): the line and its event carry that date,
    so a month-old decision never reads as today's.

    client_id "owner" — the person himself, "learner" — Mnemai's own learning (owner's rights,
    marked "выучено" so it's visible what came from learning). A heading or topic may carry tags that hide it from
    some assistants: "profile:Деньги #money", "card:Здоровье #health"."""
    fact = " ".join(fact.split())
    if not fact:
        raise ValueError("пустой факт")
    trusted = client_id in ("owner", "learner")
    client = None if trusted else get_client(vault, client_id)
    kind, _, name = where.partition(":")
    scope = PLACES.get(kind)
    if not scope:
        raise ValueError(f"неизвестное место: {where}")
    if client and not client.may_write(scope):
        raise PermissionDenied(f"{client.name} не может писать в {scope}")
    date = ru_date(said or today)
    src = {"owner": "", "learner": " · выучено"}.get(client_id, f" · {client.name if client else client_id}")
    dated = fact if status_dates(fact) else f"{fact} ({date})"
    line = f"- {dated}{src}"
    replaced: list[str] = []
    event = ""

    if kind == "profile":
        if not name.strip():
            raise ValueError("нужен раздел: profile:<заголовок>")
        rel = PROFILE
        meta, body = parse_frontmatter(vault.read_raw(rel) or TEMPLATES[PROFILE].format(today=today_str(today)))
        meta["updated"] = today_str(today)
        body, replaced = _put_fact(body, line, name.strip())
        new = dump_frontmatter(meta, body)
    elif kind == "inbox":
        rel = INBOX
        text = vault.read_raw(rel) or TEMPLATES[INBOX]
        new = text.rstrip("\n") + f"\n- {date} · {fact}{src}\n"
    elif kind == "thought":
        rel = THOUGHTS
        text = vault.read_raw(rel) or TEMPLATES[THOUGHTS]
        new = text.rstrip("\n") + f"\n- {date} · {fact}{src}\n"
    elif kind == "decisions":
        rel, new = _event_text(vault, fact + src, said or today or dt.date.today(), "решение")
    elif kind == "rules":
        rel = RULES
        meta, body = parse_frontmatter(vault.read_raw(rel) or TEMPLATES[RULES].format(today=today_str(today)))
        meta["updated"] = today_str(today)
        body, replaced = _put_fact(body, line)
        new = dump_frontmatter(meta, body)
    elif kind == "card":
        topic, tags = _split_tags(name)
        if not topic:
            raise ValueError("нужна тема: card:<тема>")
        note = vault.find_note("cards", topic)
        if note:
            rel, meta, body = note.rel, dict(note.meta), note.body
        else:
            rel = f"{CARDS}/{_slug(topic)}.md"
            meta = {
                "type": "card",
                "title": topic,
                "keywords": [w for w in re.findall(r"\w{3,}", topic.lower())][:6],
                "updated": today_str(today),
            }
            body = f"# {topic}\n"
        if tags:
            meta["tags"] = sorted(set(note.tags if note else []) | set(tags))
        meta["updated"] = today_str(today)
        body, replaced = _put_fact(body, line)
        new = dump_frontmatter(meta, body)
        if replaced:  # a status changed: worth a line in the event feed
            event = f"{topic}: {fact}"
    elif kind == "project":
        if not name.strip():
            raise ValueError("нужно имя: project:<имя>")
        note = vault.find_note("projects", name)
        if note:
            rel, meta, body = note.rel, dict(note.meta), note.body
        else:
            rel = project_rel(name)
            meta, body = _new_project(name, today)
            event = f"новый проект «{name.strip()}»"
        meta["updated"] = today_str(today)
        m = re.match(r"^(?:статус|status)\s*[:—-](.*)$", fact, re.I)
        word = m.group(1).strip().lower() if m else ""
        if word and STATUS_WORDS.get(word):
            st = STATUS_WORDS[word]
            if st != meta.get("status"):
                event = f"проект «{name.strip()}»: {meta.get('status', 'active')} → {st}"
            meta.update(status=st, status_updated=today_str(today))
        m = re.match(r"^(?:цель|goal)\b[^:—\n]*[:—]\s*(.+)$", fact, re.I)
        if m and m.group(1).strip():
            goal = m.group(1).strip()
            # the first goal stays until the owner says it changed: a goal guessed from the audience must not
            # silently replace the goal he named
            changed = bool(re.search(r"(?:изменил|изменилась|изменился|новая|теперь|вместо|передумал)", fact, re.I))
            if not str(meta.get("goal") or "").strip() or changed:
                meta["goal"] = goal
        dl = re.match(r"^(?:дедлайн|deadline|срок)\b[^:—\n]*[:—]\s*(.+)$", fact, re.I)
        if dl and dl.group(1).strip():
            meta["deadline"] = dl.group(1).strip()
        if word and STATUS_WORDS.get(word):
            # the status lives in the frontmatter; a "learned fact" line «Статус: active» in the journal is noise
            replaced = []
        else:
            body, replaced = _put_fact(body, f"- {date} · {fact}{src}" if not status_dates(fact) else line, "Журнал")
        new = dump_frontmatter(meta, body)
        if replaced and not event:
            event = f"{name.strip()}: {fact}"
    else:  # person
        if not name.strip():
            raise ValueError("нужно имя: person:<имя>")
        note = vault.find_note("people", name)
        if note:
            rel, meta, body = note.rel, dict(note.meta), note.body
        else:
            rel = f"{PEOPLE}/{_slug(name)}.md"
            meta, body = {"type": "person", "updated": today_str(today)}, f"# {name.strip()}\n"
        meta["updated"] = today_str(today)
        body, replaced = _put_fact(body, line, "Заметки")
        new = dump_frontmatter(meta, body)

    hidden = tags_of(parse_frontmatter(new)[0].get("tags"))
    if event and hidden:  # an event of a hidden topic carries its tags: assistants without access never see it
        event += " " + " ".join(f"#{t}" for t in sorted(hidden))
    ev = write_with_journal(vault, client_id, rel, new, f"{where}: {fact[:120]}")
    if replaced:
        _archive_lines(vault, rel, replaced, "заменено", today)
    if event:
        add_event(vault, event + src, said or today)
    if kind == "project" and re.match(r"^(?:статус|status)\s*[:—-]\s*(closed|закрыт|завершён|архив)", fact, re.I):
        set_project_status(vault, name, "closed", client_id, today)
    generate_now(vault, today)
    return ev


# ---------------------------------------------------------------- stale statuses: asked, not trusted silently


def _sid(rel: str, text: str) -> str:
    return "stale:" + hashlib.sha1(f"{rel}\n{text}".encode("utf-8")).hexdigest()[:12]


def stale_items(vault: Vault, today: dt.date | None = None) -> list[dict]:
    out = []
    for s in vault.stale(today, STALE_DAYS):
        title = vault.read(s.rel).title if vault.read_raw(s.rel) is not None else s.rel
        out.append(
            {
                "id": _sid(s.rel, s.text),
                "state": "stale",
                "kind": "status",
                "text": s.text,
                "where": s.rel,
                "title": title,
                "age_days": s.age_days,
                "date": s.date.isoformat(),
                "tags": sorted(s.tags),
            }
        )
    return out


@locked
def resolve_stale(vault: Vault, item_id: str, action: str, text: str = "", today: dt.date | None = None) -> dict:
    """still — the status is still true (its date moves to today); changed — new wording replaces it, the old one goes
    to the fact archive; gone — no longer relevant: moved to the fact archive (a project — closed and archived)."""
    it = next((x for x in stale_items(vault, today) if x["id"] == item_id), None)
    if not it:
        raise KeyError("этот вопрос уже закрыт")
    rel = it["where"]
    note = vault.read(rel)
    if it["text"].endswith(": проект не обновлялся"):  # a project hub nobody touched for a month
        if action == "gone":
            return set_project_status(vault, note.title, "closed", "owner", today)
        if action == "changed" and text.strip():
            return remember(
                vault,
                f"Статус: {text.strip()}" if text.strip().lower() in STATUS_WORDS else text.strip(),
                f"project:{note.title}",
                "owner",
                today,
            )
        meta = dict(note.meta)
        meta["updated"] = today_str(today)
        return write_with_journal(
            vault, "owner", rel, dump_frontmatter(meta, note.body), f"проект {note.title}: всё ещё в силе"
        )
    raw = vault.read_raw(rel) or ""
    lines = raw.splitlines()
    idx = next(
        (
            i
            for i, l in enumerate(lines)
            if l.strip(" -*") == it["text"] or l.strip().lstrip("-* ").strip() == it["text"]
        ),
        None,
    )
    if idx is None:
        raise KeyError("строка уже изменилась")
    old = lines[idx]
    stamp = f"(статус {ru_date(today)})"
    if action == "still":
        lines[idx] = re.sub(r"\((?:статус|status)\s[^()]*\)", stamp, old, flags=re.I)
        summary = f"всё ещё в силе: {it['text'][:100]}"
    elif action == "changed":
        new = " ".join(text.split())
        if not new:
            raise ValueError("пустой факт")
        lines[idx] = f"- {re.sub(r'[(]статус[^()]*[)]', '', new, flags=re.I).strip()} {stamp}"
        summary = f"обновлено: {new[:100]}"
    elif action == "gone":
        lines.pop(idx)
        summary = f"неактуально: {it['text'][:100]}"
    else:
        raise ValueError("неизвестное действие")
    ev = write_with_journal(vault, "owner", rel, "\n".join(lines) + "\n", summary)
    if action != "still":
        _archive_lines(vault, rel, [old], "заменено" if action == "changed" else "неактуально", today)
        add_event(vault, f"{it['title']}: {summary}", today)
    generate_now(vault, today)
    return ev


# ---------------------------------------------------------------- generated layers: Now and Index


def _fact_lines(body: str) -> list[str]:
    return [l for l in body.splitlines() if l.lstrip().startswith(("- ", "* "))]


DATE_RE = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")


def _line_date(line: str) -> dt.date | None:
    m = DATE_RE.search(line)
    if not m:
        return None
    try:
        return dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def generate_now(vault: Vault, today: dt.date | None = None, client: Client | None = None) -> str:
    """The 'today' layer. Without client: full version, written to «10 Now.md» (and the Index is rebuilt).
    With client: only what this assistant may see, nothing written."""
    today = today or dt.date.today()
    ok = (lambda scope: True) if client is None else client.allows
    deny = set(client.deny_tags) if client else set()
    out = [f"# Сейчас — {ru_date(today)}", "", GEN_NOTE, ""]
    me = vault.read(PROFILE) if vault.read_raw(PROFILE) else None
    if me and ok("profile") and not (me.tags & deny):
        para = next(
            (
                p.strip()
                for p in me.body.split("\n\n")
                if p.strip()
                and not p.strip().startswith(("#", ">"))
                and not p.strip().startswith("Кто я в двух-трёх фразах")
            ),
            "",
        )  # the empty template is not a fact
        if para:
            out += ["## Кто", "", para, ""]
    active = [
        n for n in vault.by_scope("projects") if str(n.meta.get("status", "active")) == "active" and not (n.tags & deny)
    ]
    if active and ok("projects"):
        out += ["## Проекты в работе", "", "| Проект | Статус | С | Цель |", "|---|---|---|---|"]
        for n in sorted(active, key=lambda n: str(n.meta.get("updated", "")), reverse=True):
            out.append(
                f"| {n.title} | {n.meta.get('status', 'active')} | {n.meta.get('started', '')} | {n.meta.get('goal', '')} |"
            )
        out.append("")
    if ok("decisions"):
        titles = hidden_titles(vault, deny)
        ev = [l for l in events(vault, 5) if not event_hidden(l, deny, titles)]
        if ev:
            out += ["## Последние события", "", *ev, ""]
    fresh = []
    for n in vault.notes():
        if n.scope not in ("cards", "projects", "people", "profile") or not ok(n.scope):
            continue
        for sec in n.sections():
            if (n.tags | sec.tags) & deny:
                continue
            for l in _fact_lines(sec.text):
                d = _line_date(l)
                if d and 0 <= (today - d).days <= FRESH_DAYS:
                    fresh.append((d, f"- {d:%d.%m} · {n.title} — {l.strip().lstrip('-* ')[:200]}"))
    if fresh:
        out += [
            f"## Свежие факты ({FRESH_DAYS} дней)",
            "",
            *[t for _, t in sorted(fresh, key=lambda x: x[0], reverse=True)[:12]],
            "",
        ]
    stale = [
        s
        for s in vault.stale(today, STALE_DAYS)
        if client is None or (client.allows(vault.read(s.rel).scope) and not (s.tags & deny))
    ][:7]
    if stale:
        out += [f"## Статусы старше {STALE_DAYS} дней — сверить", ""]
        out += [f"- {s.date:%d.%m.%Y} · {s.text}" for s in stale]
        out.append("")
    inbox = vault.read_raw(INBOX)
    if inbox and ok("inbox"):
        n = sum(1 for l in inbox.splitlines() if l.startswith("- "))
        if n:
            out += [f"Во входящих {n} неразобранных фактов.", ""]
    text = "\n".join(out)
    if client is None:
        vault.write_raw(NOW, text)
        generate_index(vault)
    return text


def generate_index(vault: Vault) -> str:
    """«70 Memory/Index.md»: find a word in «по чему находится» → open the file."""

    def kw(n):
        return ", ".join(str(k) for k in n.keywords) or ", ".join(re.findall(r"\w{3,}", n.title.lower())[:4])

    def cnt(n):
        return len(_fact_lines(n.body))

    out = [
        "# Индекс памяти",
        "",
        GEN_NOTE,
        "",
        "Нашёл слово в колонке «по чему находится» — открывай файл из колонки «где лежит».",
        "",
    ]
    projects = sorted(
        vault.by_scope("projects"), key=lambda n: (str(n.meta.get("status", "active")) != "active", n.title.lower())
    )
    if projects:
        out += [
            "## Проекты",
            "",
            "| Проект | Статус | Фактов | Где лежит | По чему находится |",
            "|---|---|---|---|---|",
        ]
        out += [f"| {n.title} | {n.meta.get('status', 'active')} | {cnt(n)} | `{n.rel}` | {kw(n)} |" for n in projects]
        out.append("")
    cards = sorted(vault.by_scope("cards"), key=lambda n: n.title.lower())
    if cards:
        out += ["## Карточки", "", "| Карточка | Фактов | Где лежит | По чему находится |", "|---|---|---|---|"]
        out += [f"| {n.title}{' 🔒' if n.tags else ''} | {cnt(n)} | `{n.rel}` | {kw(n)} |" for n in cards]
        out.append("")
    people = sorted(vault.by_scope("people"), key=lambda n: n.title.lower())
    if people:
        out += ["## Люди", "", "| Человек | Фактов | Где лежит |", "|---|---|---|"]
        out += [f"| {n.title} | {cnt(n)} | `{n.rel}` |" for n in people]
        out.append("")
    text = "\n".join(out)
    vault.write_raw(INDEX, text)
    return text


# ---------------------------------------------------------------- context for an assistant


def build_context(vault: Vault, client: Client, today: dt.date | None = None) -> str:
    deny = set(client.deny_tags)
    parts = [
        f"## Память владельца (Mnemai) · для {client.name} · {ru_date(today)}",
        "Это то, что владелец разрешил тебе знать о нём. Опирайся на это, не переспрашивай известное. "
        "Если факт помечен датой статуса и он старый — уточни. Новое важное предлагай сохранить в память.",
    ]
    generate_now(vault, today)  # keep «10 Now.md» fresh for the owner
    parts.append(generate_now(vault, today, client))  # what this assistant may see
    order = [
        ("profile", "Обо мне"),
        ("rules", "Правила"),
        ("projects", "Проекты"),
        ("cards", "Карточки"),
        ("people", "Люди"),
        ("decisions", "События и решения"),
        ("inbox", "Входящие"),
    ]
    for scope, title in order:
        if not client.allows(scope):
            continue
        notes = vault.by_scope(scope)
        if scope == "projects":
            notes = [n for n in notes if str(n.meta.get("status", "active")) == "active"]
        if scope == "decisions":
            titles = hidden_titles(vault, deny)
            items = [l for l in events(vault, 25) if not event_hidden(l, deny, titles)]
            if items:
                parts.append(f"=== {title} ===\n" + "\n".join(items))
            continue
        chunks = []
        for n in notes:
            text = n.visible_text(deny).strip()
            if not text:
                continue
            if scope == "people":
                facts = [l.strip(" -") for l in text.splitlines()[1:] if l.strip() and not l.startswith("#")][:3]
                chunks.append(f"- {n.title}: {'; '.join(facts)}")
            elif scope == "inbox":
                items = [l for l in text.splitlines() if l.startswith("- ")][:25]
                chunks.append("\n".join(items))
            elif scope == "cards":
                keys = f" (ключи: {', '.join(map(str, n.keywords))})" if n.keywords else ""
                chunks.append(f"### {n.title}{keys}\n" + "\n".join(_fact_lines(text)))
            elif scope == "projects":
                head = f"### Проект {n.title} · {n.meta.get('status', 'active')}" + (
                    f" · цель: {n.meta['goal']}" if n.meta.get("goal") else ""
                )
                chunks.append(head + "\n" + "\n".join(_fact_lines(text)[-15:]))
            else:  # the profile; its empty template line is not a fact
                chunks.append("\n".join(l for l in text.splitlines() if not l.startswith("Кто я в двух-трёх фразах")))
        if chunks:
            parts.append(f"=== {title} ===\n" + "\n\n".join(chunks))
    return "\n\n".join(parts)


def split_chunks(text: str, limit: int = CHUNK_LIMIT) -> list[str]:
    chunks, cur = [], ""
    for line in text.splitlines(keepends=True):
        while len(line) > limit:
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(line[:limit])
            line = line[limit:]
        if len(cur) + len(line) > limit:
            chunks.append(cur)
            cur = ""
        cur += line
    if cur:
        chunks.append(cur)
    return chunks or [""]


SCOPE_RU = {
    "profile": "профиль",
    "rules": "правила",
    "projects": "проекты",
    "cards": "карточки",
    "people": "люди",
    "decisions": "события и решения",
    "inbox": "входящие",
    "notes": "заметки",
    "money": "деньги",
    "health": "здоровье",
    "private": "личное",
}


def context_for(
    vault: Vault, client_id: str, part: int | None = None, log: bool = True, today: dt.date | None = None
) -> tuple[str, int]:
    """Context text for a client. Returns (text, total_parts). part=None → whole text."""
    client = get_client(vault, client_id)
    if not client.enabled:
        return "", 0
    text = build_context(vault, client, today)
    chunks = split_chunks(text)
    if log and (part in (None, 0)):
        ru = lambda xs: ", ".join(SCOPE_RU.get(x, x) for x in xs)  # noqa: E731
        log_event(
            vault,
            client_id,
            "read",
            f"контекст: {ru(client.scopes)}" + (f" · скрыто: {ru(client.deny_tags)}" if client.deny_tags else ""),
        )
    if part is None:
        return text, len(chunks)
    if part >= len(chunks):
        return "", len(chunks)
    head = f"[Память владельца, часть {part + 1} из {len(chunks)}]\n"
    return head + chunks[part], len(chunks)
