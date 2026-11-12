"""The learning loop and the owner's say over it.

run()     — one pass: read new material from every enabled source, extract, reinforce, decide, write.
review()  — the owner's answer to a queue item: keep, edit, no, never learn this, forget, keep both.
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import threading

from ..journal import log_event, write_with_journal
from ..memory import generate_now, remember, ru_date
from ..vault import PROFILE, RULES, Vault, line_tags
from . import settings as S
from .brains import make_brain
from .ledger import IN_MEMORY, Ledger, now, said_date, same_meaning, similar
from .sources import READERS, load_cursors, save_cursors

CARD_FOR_TAG = {"money": "Деньги #money", "health": "Здоровье #health", "private": "Личное #private"}
AI_CHAT_SOURCES = {"claude_code", "chatgpt_export"}
_lock = threading.Lock()


# ---------------------------------------------------------------- what memory already knows


def known_text(vault: Vault, limit: int = 6000, deny: set | None = None) -> str:
    """A compact view of memory for the brain: avoids repeats and spots contradictions. deny — the tags hidden from
    the AI the brain runs on: a cloud brain gets memory under the same rules as that AI in the chat."""
    from ..memory import event_hidden, events, hidden_titles

    deny = set(deny or ())
    out = []
    for rel in (PROFILE, RULES):
        if vault.read_raw(rel) is None:
            continue
        note = vault.read(rel)
        raw = note.visible_text(deny)
        out += [l.strip() for l in raw.splitlines() if l.strip().startswith(("-", "#")) or len(l.strip()) > 30]
    cards = [n for n in vault.by_scope("cards") if not (n.tags & deny)]
    if cards:
        out.append("КАРТОЧКИ (темы, пиши в существующую): " + ", ".join(n.title for n in cards))
    for n in cards:
        body = n.visible_text(deny)
        out += [f"[{n.title}] {l.strip()}" for l in body.splitlines() if l.lstrip().startswith("- ")][-12:]
    titles = hidden_titles(vault, deny)
    out += [l for l in events(vault, 30) if not event_hidden(l, deny, titles)]
    for n in vault.by_scope("projects"):
        if not (n.tags & deny):
            out.append(f"Проект {n.title}: {n.meta.get('status', '')} {n.meta.get('goal', '')}".strip())
    for n in vault.by_scope("people"):
        if not (n.tags & deny):
            out.append(f"Человек {n.title}")
    text = "\n".join(l for l in out if not l.startswith("---"))
    return text[:limit]


def _section_tags(note, line: str) -> set:
    for sec in note.sections():
        if line.strip() and line.strip() in sec.text:
            return set(sec.tags)
    return set()


def brain_deny(vault: Vault, brain) -> set:
    """What the AI behind this brain may not see — the column of that AI in «Кто из ИИ что видит»."""
    from ..clients import get_client

    name = getattr(brain, "name", "")
    if name == "claude_code" or (name == "api" and getattr(brain, "provider", "") == "anthropic"):
        client = "claude"
    elif name == "api":
        ep = (getattr(brain, "endpoint", "") or "").lower()
        client = "openrouter" if "openrouter" in ep else "gemini" if "generativelanguage" in ep else "chatgpt"
    else:  # on this computer: nothing leaves it
        return set()
    return set(get_client(vault, client).deny_tags) or (set() if client == "claude" else {"money", "health", "private"})


def memory_lines(vault: Vault) -> list[tuple[str, str]]:
    """Every content line of memory (bullets and prose), skipping frontmatter and headings."""
    res = []
    for n in vault.notes():
        raw = vault.read_raw(n.rel) or ""
        in_fm = raw.startswith("---")
        for i, l in enumerate(raw.splitlines()):
            if in_fm:
                if i > 0 and l.strip() == "---":
                    in_fm = False
                continue
            s = l.strip()
            if s and not s.startswith(("#", ">")):
                res.append((n.rel, l))
    return res


# ---------------------------------------------------------------- policy


def route(it: dict) -> str:
    """Sensitive facts go to hidden places — a profile section or a card that carries the tag — so assistants
    that may not see money / health / private never get them."""
    if not it["tags"]:
        return it["where"]
    if it["where"].startswith(("profile:", "card:")):  # keep the place, but it must carry the hidden tags
        kind, heading = it["where"].split(":", 1)
        missing = [f"#{t}" for t in it["tags"] if f"#{t}" not in heading]
        return kind + ":" + " ".join([heading.strip(), *missing])
    return "card:" + CARD_FOR_TAG[it["tags"][0]] + "".join(f" #{t}" for t in it["tags"][1:])


def mode_for(it: dict, settings: dict) -> str:
    """The mode of the source where the fact was seen this time (an old sighting in a source switched off later
    must not silence a new one)."""
    srcs = settings["sources"]
    seen = [it["last_source"]] if it.get("last_source") in srcs else it["sources"]
    modes = [srcs[s]["mode"] if srcs.get(s, {}).get("enabled") else "off" for s in seen if s in srcs]
    if it.get("correction"):
        c = srcs["corrections"]
        modes = [c["mode"] if c["enabled"] else "off"]
    order = ["off", "observe", "approve", "mixed", "quiet"]  # most careful source wins
    return min(modes, key=order.index) if modes else "off"


def never_hit(it: dict, settings: dict) -> bool:
    hay = (it["text"] + " " + it.get("key", "")).lower()
    return any(p.strip().lower() in hay for p in settings.get("never", []) if p.strip())


TAG_RU = {"money": "деньги", "health": "здоровье", "private": "личное"}


def decide_why(it: dict, settings: dict, can_ask: bool = False) -> tuple[str, str]:
    """What to do with an item the owner hasn't decided yet — and why, in plain words.

    There is no waiting queue. can_ask — it was said in a conversation in Mnemai: what needs the owner (something
    personal, a contradiction, "always ask" mode) is asked right there, once. Anywhere else Mnemai decides by itself:
    personal goes to a hidden part, the newer fact replaces the older one, a weak guess waits to be seen again."""
    mode = mode_for(it, settings)
    conf = round(it["confidence"] * 100)
    if mode == "off":
        return "skip", "источник выключен"
    if never_hit(it, settings):
        return "skip", "тема в списке «никогда не учиться»"
    if mode == "observe":
        return "observed", "источник в режиме «только смотрит»: показываю, но не записываю"
    if mode == "approve":
        if can_ask:
            return "ask", "режим «всё спрашивает»: уточню в разговоре"
        return "observed", "режим «всё спрашивает»: из других мест сама не записываю"
    if it.get("contradicts") and mode != "quiet":
        if can_ask:
            return "ask", f"противоречит памяти («{it['contradicts'][:80]}») — уточню в разговоре"
        return "replace", f"новее того, что было в памяти («{it['contradicts'][:80]}»): заменила, прежнее — в архиве"
    if mode == "quiet":
        return "write", "режим «всё сама»: записала, откатить можно в истории"
    if it["tags"]:
        what = ", ".join(TAG_RU.get(t, t) for t in it["tags"])
        if can_ask:
            return "ask", f"это {what} — личное, уточню в разговоре"
        return "write", f"это {what} — записала в скрытую часть, её видят только ИИ с доступом"
    auto = round(settings["auto_confidence"] * 100)
    if it["confidence"] >= settings["auto_confidence"]:
        rep = f", встретилось {it['count']} раза" if it.get("count", 1) > 1 else ""
        return "write", f"уверенность {conf}% (порог {auto}%){rep}, не личное — записала сама"
    return "weak", f"уверенность {conf}% — ниже порога {auto}%, жду, когда повторится"


def decide(it: dict, settings: dict, can_ask: bool = False) -> str:
    return decide_why(it, settings, can_ask)[0]


# ---------------------------------------------------------------- live feed

_live: dict = {}


def emit(vault: Vault, stage: str, text: str, **extra) -> dict:
    """One line of the live feed: читаю → поняла → записала / спрашиваю / жду / уже знаю / пропустила."""
    ev = {"ts": dt.datetime.now().isoformat(timespec="milliseconds"), "stage": stage, "text": text[:300], **extra}
    if stage in ("записала", "подтвердилось"):
        from .. import achievements

        achievements.event(vault, "learn", stage=stage)
    buf = _live.setdefault(str(vault.root), [])
    buf.append(ev)
    del buf[:-300]
    f = vault.service / "learn" / "live.jsonl"
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        from ..fsutil import append_text

        append_text(f, json.dumps(ev, ensure_ascii=False) + "\n")
        if f.stat().st_size > 400_000:  # keep the file small
            keep = f.read_text(encoding="utf-8").splitlines()[-500:]
            f.write_text("\n".join(keep) + "\n", encoding="utf-8")
    except OSError:
        pass
    return ev


def live(vault: Vault, since: str = "", limit: int = 80) -> list:
    buf = _live.get(str(vault.root))
    if buf is None:
        f = vault.service / "learn" / "live.jsonl"
        buf = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()[-300:]] if f.exists() else []
        _live[str(vault.root)] = buf
    return [e for e in buf if e["ts"] > since][-limit:]


def _write(vault: Vault, it: dict, by: str) -> None:
    fact = it["text"] + (f" · {it['url']}" if it.get("url") else "")
    ev = remember(vault, fact, route(it), "learner", said=said_date(it.get("said_at")))
    it.update(state="written" if by == "auto" else "confirmed", event_id=ev["id"], decided_by=by, written_at=now())


def _in_memory_already(it: dict, lines: list[tuple[str, str]]) -> bool:
    if it.get("kind") == "rule" and any(rel == RULES and same_meaning(it["text"], l) for rel, l in lines):
        return True  # the owner's own rule in other words
    return any(similar(it["text"], l) >= 0.85 for _, l in lines)


# ---------------------------------------------------------------- one pass


def status(vault: Vault) -> dict:
    f = vault.service / "learn" / "runs.jsonl"
    runs = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()[-20:]] if f.exists() else []
    led = Ledger(vault)
    lc = vault.service / "learn" / "last_check"
    return {
        "counts": led.counts(),
        "queue": len(led.queue()),
        "runs": runs[::-1],
        "running": _lock.locked(),
        "last_check": lc.read_text(encoding="utf-8") if lc.exists() else "",
    }


def safe_brain(settings: dict, report: dict):
    """The chosen brain, or explicit signals only when it can't be made (a key or a model not filled in yet):
    "запомни" and corrections keep working, the reason goes to the report."""
    try:
        return make_brain(settings)
    except Exception as e:
        from .brains import NoModelBrain

        report["errors"].append(f"чем понимает тексты: {e}")
        return NoModelBrain()


def run(vault: Vault, initial: bool = False, only: list[str] | None = None, brain=None, progress=None) -> dict:
    """One learning pass. Safe to call from a timer: a second call while one is running returns at once."""
    from ..agent import profile as P

    if not P.memory_on(vault):
        return {"skipped": "память выключена"}
    if not _lock.acquire(blocking=False):
        return {"skipped": "уже учится"}
    try:
        return _run(vault, initial, only, brain, progress)
    finally:
        _lock.release()


def _run(vault, initial, only, brain, progress) -> dict:
    settings = S.load(vault)
    report = new_report(initial)
    if settings.get("demo"):
        report["skipped"] = "демо: обучение выключено, чтобы не читать твой компьютер"
        return report
    if settings["paused"] and not initial:
        report["skipped"] = "пауза"
        return report
    brain = brain or safe_brain(settings, report)
    if hasattr(brain, "vault"):
        brain.vault = vault
    cursors = load_cursors(vault)
    led = Ledger(vault)
    lines = memory_lines(vault)
    known = known_text(vault, deny=brain_deny(vault, brain))
    days = settings["initial"]["days"]
    for sid, reader in READERS.items():
        src = settings["sources"][sid]
        if (only and sid not in only) or not S.allowed(settings, sid):
            continue
        if progress:
            progress(f"читаю: {S.SOURCES[sid]['name']}")
        before = copy.deepcopy(cursors.get(sid, {}))
        cur = cursors.setdefault(sid, {})
        try:
            eps = reader(vault, src["options"], cur, days, settings["max_episodes_per_run"])
            if eps:
                emit(
                    vault, "читаю", f"{S.SOURCES[sid]['name']}: {len(eps)} новых", source=sid, quote=eps[-1].text[:160]
                )
            if progress and eps:
                progress(f"разбираю: {S.SOURCES[sid]['name']} — {len(eps)} реплик")
            cands = brain.extract(eps, known) if eps else []
        except Exception as e:  # source or brain failed: retry next time
            cursors[sid] = before
            report["errors"].append(f"{S.SOURCES[sid]['name']}: {e}")
            continue
        report["episodes"] += len(eps)
        report["candidates"] += len(cands)
        report["by_source"][sid] = {"episodes": len(eps), "candidates": len(cands)}
        for c in cands:
            c["source"] = c.get("source") or sid
            consider(vault, led, c, settings, report, lines)
    report["to_forget"] = offer_forgetting(led, settings)
    led.save()
    save_cursors(vault, cursors)
    if initial:
        settings["initial"]["done"] = True
        S.save(vault, settings)
    if report["written"]:
        generate_now(vault)
        _portrait(vault)
    f = vault.service / "learn" / "runs.jsonl"
    f.parent.mkdir(parents=True, exist_ok=True)
    (vault.service / "learn" / "last_check").write_text(report["ts"], encoding="utf-8")
    if report["episodes"] or report["errors"] or report["to_forget"] or initial:  # empty checks aren't history
        from ..fsutil import append_text

        append_text(f, json.dumps(report, ensure_ascii=False) + "\n")
    if report["written"] or report["queued"]:
        log_event(
            vault,
            "learner",
            "learn",
            f"обучение: записано {report['written']}, на одобрение {report['queued']}",
            [],
            {"episodes": report["episodes"]},
        )
    return report


def consider(
    vault: Vault, led: Ledger, c: dict, settings: dict, report: dict, lines: list, can_ask: bool = False
) -> dict | None:
    """One candidate: reinforce or add, then decide what to do with it."""
    if c.get("correction") and not settings["sources"]["corrections"]["enabled"]:
        return None
    if led.seen(c):
        return None
    it, is_new = led.add(c)
    it["last_source"] = c.get("source", "")
    report["new" if is_new else "reinforced"] += 1
    if (
        it["state"]
        in ("rejected", "forgotten", "confirmed", "written", "observed", "known", "skipped", "forget_pending", "asking")
        and not is_new
    ):
        if (
            it["state"] in ("written", "confirmed")
            and it.get("kind") == "rule"
            and similar(c["text"], it["text"]) < 0.85
        ):  # the same rule in newer words: the line is rewritten, not doubled
            try:
                ev = _replace_line(
                    vault, it["text"], f"- {c['text']} ({ru_date()}) · выучено", f"правило уточнено: {c['text'][:100]}"
                )
                if ev:
                    it["text"] = c["text"]
            except Exception as e:
                report["errors"].append(f"запись: {e}")
        if it["state"] in ("written", "confirmed", "known"):
            emit(
                vault,
                "подтвердилось",
                it["text"],
                why=f"встретилось ещё раз, всего {it['count']}",
                item=it["id"],
                source=c.get("source", ""),
            )
        return it  # the owner already decided, or it's in memory
    if is_new and _in_memory_already(it, lines):
        it["state"] = "known"
        emit(vault, "уже знаю", it["text"], why="это уже есть в памяти", item=it["id"], source=c.get("source", ""))
        return it
    st, why = decide_why(it, settings, can_ask)
    it["why"] = why
    stage = {
        "skip": "пропустила",
        "write": "записала",
        "pending": "спрашиваю",
        "ask": "спрашиваю",
        "replace": "заменила",
        "conflict": "спрашиваю",
        "observed": "заметила",
        "weak": "жду повтора",
    }[st]
    if st == "skip":
        it["state"] = "skipped"
    elif st == "replace":
        try:
            ev = resolve_conflict(vault, it, settings)
            if ev:
                it.update(state="written", event_id=ev.get("id", ""), decided_by="auto", written_at=now())
            else:
                _write(vault, it, "auto")
            report["written"] += 1
        except Exception as e:
            it["state"] = "weak"
            report["errors"].append(f"запись: {e}")
    elif st == "ask":
        it["state"] = "asking"
    elif st == "write":
        try:
            _write(vault, it, "auto")
            lines.append((route(it), "- " + it["text"]))
            report["written"] += 1
        except Exception as e:
            it["state"] = "pending"
            stage, why = "спрашиваю", f"не смогла записать: {e}"
            report["errors"].append(f"запись: {e}")
    else:
        if st in ("pending", "conflict") and it["state"] not in ("pending", "conflict"):
            report["queued"] += 1
        elif st == "observed" and it["state"] != "observed":
            report["observed"] += 1
        elif st == "weak":
            report["weak"] += 1
        it["state"] = st
    emit(
        vault,
        stage,
        it["text"],
        why=why,
        item=it["id"],
        state=it["state"],
        where=route(it),
        source=c.get("source", ""),
        quote=(c.get("evidence") or "")[:200],
    )
    return it


def _ask_paused(vault: Vault, chat_id: str, settings: dict) -> bool:
    """One question about memory per conversation per cooldown, not one per little fact: the owner is not to be
    asked every minute. While paused, what would have been asked is decided silently — personal goes into the
    hidden part, a newer fact replaces the older one — and the feed and History still show it."""
    minutes = float(settings.get("ask_cooldown_minutes") or 0)
    if minutes <= 0 or not chat_id:
        return False
    from ..chat import engine as CH

    try:
        at = CH.load_chat(vault, chat_id).get("learn_ask_at")
    except (KeyError, OSError):
        return False
    if not at:
        return False
    try:
        last = dt.datetime.fromisoformat(str(at))
    except ValueError:
        return False
    return (dt.datetime.now() - last).total_seconds() < minutes * 60


def learn_episodes(vault: Vault, eps: list, source: str, brain=None) -> dict:
    """Learn right now from fresh episodes. From a conversation in Mnemai (source "mnema_chat", ref "<chat>#<n>") what
    needs the owner is asked in that conversation: one question at a time, shown under the messages."""
    """Learn right now from fresh episodes (the wrapper chat): no cursors, live feed on."""
    from ..agent import profile as P

    settings = S.load(vault)
    report = new_report()
    if not P.memory_on(vault):
        return report
    if settings.get("demo") or settings["paused"] or not S.allowed(settings, source) or not eps:
        return report
    with _lock:
        brain = brain or safe_brain(settings, report)
        if hasattr(brain, "vault"):  # «Что ушло наружу» knows about it
            brain.vault = vault
        emit(vault, "читаю", eps[-1].text[:160], source=source)
        try:
            cands = brain.extract(eps, known_text(vault, deny=brain_deny(vault, brain)))
        except Exception as e:
            emit(vault, "ошибка", f"не смогла разобрать: {e}", source=source)
            report["errors"].append(str(e))
            return report
        if not cands:
            emit(vault, "ничего нового", "в этом сообщении нечего запоминать", source=source)
        led = Ledger(vault)
        lines = memory_lines(vault)
        chat_id = eps[-1].ref.split("#")[0] if source == "mnema_chat" and "#" in eps[-1].ref else ""
        ask_ready = bool(chat_id) and not _ask_paused(vault, chat_id, settings)
        asked = None
        for c in cands:
            c["source"] = source
            it = consider(vault, led, c, settings, report, lines, can_ask=ask_ready and asked is None)
            if it and it.get("state") == "asking" and asked is None:
                asked = it
        led.save()
        if asked:
            _ask_in_chat(vault, chat_id, asked)
        if report["written"]:
            generate_now(vault)
            _portrait(vault)
    return report


def _portrait(vault: Vault) -> None:
    """New facts about the owner: the portrait at the top of the profile is rebuilt in the background."""
    from .. import portrait

    portrait.refresh_later(vault)


def _ask_in_chat(vault: Vault, chat_id: str, it: dict) -> None:
    """Put one question about memory under the conversation; the next one waits until this is answered."""
    from ..chat import engine as CH

    kind = "conflict" if it.get("contradicts") else "personal" if it.get("tags") else "confirm"
    q = {"item": it["id"], "kind": kind, "text": it["text"], "old": it.get("contradicts", "")}

    def put(c):
        if not c.get("learn_ask"):
            c["learn_ask"] = q
            c["learn_ask_at"] = dt.datetime.now().isoformat(timespec="seconds")

    try:
        CH.modify_chat(vault, chat_id, put)
    except KeyError:
        it["state"] = "weak"  # the conversation is gone: wait to see it again


def new_report(initial: bool = False) -> dict:
    return {
        "ts": now(),
        "initial": initial,
        "episodes": 0,
        "candidates": 0,
        "new": 0,
        "reinforced": 0,
        "written": 0,
        "queued": 0,
        "observed": 0,
        "weak": 0,
        "errors": [],
        "by_source": {},
    }


def offer_forgetting(led: Ledger, settings: dict, today: dt.datetime | None = None) -> int:
    """Nothing is queued for forgetting any more: old learned facts stay, the History undoes any of them."""
    return 0


# ---------------------------------------------------------------- the owner's answers


def _find_line(vault: Vault, needle: str) -> tuple[str, str] | None:
    best, score = None, 0.0
    for rel, l in memory_lines(vault):
        s = similar(needle, l)
        if s > score:
            best, score = (rel, l), s
    return best if best and score >= 0.6 else None


def _replace_line(
    vault: Vault, needle: str, new_line: str | None, summary: str, insert_after: bool = False
) -> dict | None:
    """Find the memory line closest to needle and replace it, delete it (new_line None) or add after it."""
    with vault.lock():
        return _replace_line_now(vault, needle, new_line, summary, insert_after)


def _replace_line_now(vault, needle, new_line, summary, insert_after=False):
    hit = _find_line(vault, needle)
    if not hit:
        return None
    rel, line = hit
    lines = (vault.read_raw(rel) or "").splitlines()
    idx = lines.index(line)
    if new_line is None:
        lines.pop(idx)
    elif insert_after:
        lines.insert(idx + 1, new_line)
    else:
        lines[idx] = new_line
    return write_with_journal(vault, "owner", rel, "\n".join(lines) + "\n", summary)


REVISE = """{mark}
Строка из памяти устарела в одном месте. Перепиши её с учётом нового факта, сохранив всё остальное, что в ней есть.
Верни только новую строку, без кавычек и пояснений. Если строка начиналась с "- ", сохрани это.
Старая строка: {old}
Новый факт: {new}"""


def resolve_conflict(vault: Vault, it: dict, settings: dict) -> dict | None:
    """ "Новое верно" must never lose what else the old line said.
    Same fact → replace. The line says more → the brain rewrites it keeping the rest. No brain → add next to it."""
    hit = _find_line(vault, it["contradicts"])
    if not hit:
        return None
    _, old = hit
    new_line = f"- {it['text']} ({ru_date()}) · выучено"
    if similar(old, it["text"]) >= 0.5:
        return _replace_line(vault, old, new_line, f"обновлено: {it['text'][:100]}")
    brain = None if settings.get("demo") else make_brain(settings)
    if brain is not None and hasattr(brain, "vault"):
        brain.vault = vault
    try:
        note = vault.read(hit[0])
        hidden_line = bool(brain_deny(vault, brain) & (note.tags | line_tags(old) | _section_tags(note, old)))
    except Exception:
        hidden_line = True
    if hidden_line:  # a hidden fact never goes to an AI that may not see it: plain replacement
        brain = None
    if brain is not None and hasattr(brain, "ask"):
        try:
            from .sources import BRAIN_MARK

            out = (
                (getattr(brain, "_ask_safe", None) or brain.ask)(
                    REVISE.format(mark=BRAIN_MARK, old=old.strip(), new=it["text"])
                )
                .strip()
                .strip('"')
                .splitlines()
            )
            line = next((l for l in out if l.strip()), "").rstrip()
            if line and len(line) <= max(400, len(old) * 2) and not line.startswith("{"):
                if old.lstrip().startswith("- ") and not line.lstrip().startswith("- "):
                    line = "- " + line
                return _replace_line(vault, old, line + f" ({ru_date()}) · выучено", f"обновлено: {it['text'][:100]}")
        except Exception:
            pass
    return _replace_line(vault, old, new_line, f"дополнено: {it['text'][:100]}", insert_after=True)


def review(vault: Vault, item_id: str, action: str, text: str = "", where: str = "") -> dict:
    """keep | edit | reject | never | forget | keep_old | keep_both"""
    settings = S.load(vault)
    led = Ledger(vault)
    it = led.get(item_id)
    if not it:
        raise KeyError("нет такого пункта")
    st = it["state"]
    if action == "keep" and st in IN_MEMORY:
        return it  # the same question answered again from an old card: the fact is already in memory
    if action in ("keep", "edit"):
        if action == "edit":
            it["prev_text"] = it["text"]
            it["text"] = " ".join((text or it["text"]).split())
            it["where"] = where or it["where"]
        if st == "forget_pending":
            it.update(state="confirmed", decided_by="owner")
        elif st in IN_MEMORY and action == "edit":
            _replace_line(
                vault,
                it.get("prev_text") or it["text"],
                f"- {it['text']} ({ru_date()}) · выучено",
                f"исправлено: {it['text'][:100]}",
            )
            it.update(state="confirmed", decided_by="owner")
        elif st in ("conflict", "asking") and it.get("contradicts"):
            ev = resolve_conflict(vault, it, settings)
            if ev:
                it.update(state="confirmed", event_id=ev["id"], decided_by="owner")
            else:
                _write(vault, it, "owner")
        else:
            _write(vault, it, "owner")
    elif action == "keep_both":
        _write(vault, it, "owner")
    elif action in ("reject", "keep_old"):
        it.update(state="rejected", decided_by="owner")
    elif action == "never":
        it.update(state="rejected", decided_by="owner")
        phrase = it.get("key") or it["text"][:40]
        if phrase not in settings["never"]:
            settings["never"].append(phrase)
            S.save(vault, settings)
    elif action == "forget":
        _replace_line(vault, it["text"], None, f"забыто: {it['text'][:100]}")
        it.update(state="forgotten", decided_by="owner")
    else:
        raise ValueError("неизвестное действие")
    led.save()
    generate_now(vault)
    return it


def review_all(vault: Vault, action: str, state: str = "pending") -> int:
    """Accept everything that waits. `keep` also takes the questions still standing in conversations: one answer
    for all instead of one per little fact."""
    led = Ledger(vault)
    states = {state} | ({"asking"} if action == "keep" else set())
    ids = [i["id"] for i in led.items if i["state"] in states]
    for i in ids:
        review(vault, i, action)
    return len(ids)


# ---------------------------------------------------------------- background


class Learner(threading.Thread):
    """Runs a pass every N minutes inside the app. Stops with the app."""

    def __init__(self, vault: Vault):
        super().__init__(daemon=True, name="mnema-learner")
        self.vault = vault
        self.stop_event = threading.Event()
        self.last: dict = {}

    def run(self) -> None:
        self.stop_event.wait(20)  # let the app start first
        while not self.stop_event.is_set():
            try:
                s = S.load(self.vault)
                background = [k for k, x in s["sources"].items() if x.get("enabled") and k != "mnema_chat"]
                if background and not s["paused"] and not s.get("demo"):
                    # the first pass looks back over the "first learning" horizon, later ones only take what's new
                    self.last = run(self.vault, initial=not s["initial"]["done"])
            except Exception as e:  # never kill the app
                self.last = {"errors": [str(e)]}
            minutes = max(1, S.load(self.vault)["interval_minutes"])
            nxt = dt.datetime.now() + dt.timedelta(minutes=minutes)
            try:
                f = self.vault.service / "learn" / "next_check"
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(nxt.isoformat(timespec="seconds"), encoding="utf-8")
            except OSError:
                pass
            self.stop_event.wait(minutes * 60)

    def stop(self) -> None:
        self.stop_event.set()
