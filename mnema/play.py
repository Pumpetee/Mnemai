"""Things to try and to show: «С памятью и без», «Насколько Mnemai тебя знает», «Знакомство».

- compare — one question to the connected AIs twice: as a plain chat (no memory) and through Mnemai (with memory),
  so the difference is seen at once;
- quiz — facts from the memory, one by one: true / no longer so / wrong. Every answer fixes the memory: a true status
  gets today's date, a changed one is rewritten, a wrong one goes to the fact archive. The score is what is shared;
- interview — the first-run questions, saved as ordinary facts (nothing is overwritten, unlike «mnema interview»).

Nothing here sends the memory anywhere but to the AIs the owner already uses, by their access rules.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
import threading

from .journal import write_with_journal
from .locks import locked
from .vault import CARDS, PEOPLE, PROFILE, PROJECT_HUB, PROJECTS, Vault

# ---------------------------------------------------------------- with memory and without

COMPARE_QUESTION = "Что ты знаешь обо мне? И что мне важнее всего сделать на этой неделе?"
SHORT = "Ответь коротко, не больше 70 слов, без вступлений."
MAX_MODELS = 3


def compare_models(vault: Vault) -> list[str]:
    """Up to three connected AIs: the one answering now, then one model of each other cloud AI, the model on this
    computer last."""
    from .chat import engine as CH, providers as PR

    first = CH.default_model(vault)
    out = [first] if first else []
    for p in sorted(PR.status(vault), key=lambda p: p["id"] in ("local", "ollama", "strata")):
        if len(out) >= MAX_MODELS:
            break
        if not p["ready"] or not p["models"] or any(r.partition(":")[0] == p["id"] for r in out):
            continue
        m = next((x for x in p["models"] if x["id"]), p["models"][0])
        out.append(f"{p['id']}:{m['id']}")
    return out


def compare(vault: Vault, question: str = "", models: list[str] | None = None) -> dict:
    """{question, results: [{ref, name, plain, mine, error}]} — each AI answers twice, the pairs run side by side."""
    from .agent import profile as P
    from .chat import consortium as CO, engine as CH, providers as PR

    if not P.memory_on(vault):
        raise ValueError("Память выключена: сравнивать не с чем. Включи её — переключатель «Память» внизу слева.")
    q = " ".join((question or "").split())[:600] or COMPARE_QUESTION
    refs = [r for r in (models or compare_models(vault)) if r][:MAX_MODELS]
    if not refs:
        raise ValueError("Нет подключённых ИИ: Настройки → ИИ и модели.")
    lang = P.load(vault).get("lang") or "en"
    lang_line = f"Язык ответа: {CH.LANG_NAMES.get(lang, lang)}."
    results = [{"ref": r, "name": CO.speaker_name(r), "plain": "", "mine": "", "error": ""} for r in refs]

    def one(i: int, with_memory: bool) -> None:
        res = results[i]
        try:
            pid, model = CH.split_model(res["ref"])
            if with_memory:
                system = CH.system_prompt(vault, pid, log=True, query=q, model=model) + "\n\n" + SHORT
            else:  # what the same AI says as a plain chat, knowing nothing about the person
                system = f"Ты — ИИ-ассистент. {SHORT} {lang_line}"
            text = PR.complete(
                vault,
                pid,
                model,
                system,
                [{"role": "user", "text": q}],
                meta={"purpose": "сравнение с памятью и без"},
            )
            res["mine" if with_memory else "plain"] = CH.strip_thinking(text).strip()
        except Exception as e:  # one AI failing doesn't spoil the others
            res["error"] = str(e)[:300]

    threads = [threading.Thread(target=one, args=(i, w), daemon=True) for i in range(len(refs)) for w in (False, True)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=240)
    return {"question": q, "results": results}


# ---------------------------------------------------------------- the quiz

QUIZ_SIZE = 10
_TAIL = re.compile(r"\s*\((\d{1,2}\.\d{1,2}\.\d{4})\)\s*$")
_SRC = re.compile(r"\s*·\s*(выучено|[\w .-]{1,30})$")


def _quiz_notes(vault: Vault) -> list:
    out = []
    for n in vault.notes():
        parts = n.rel.split("/")
        if (
            n.rel == PROFILE
            or n.rel.startswith(CARDS + "/")
            or (parts[0] == PEOPLE and len(parts) == 2)
            or (parts[0] == PROJECTS and len(parts) == 3 and parts[2] == PROJECT_HUB)
        ):
            out.append(n)
    return out


def _qid(rel: str, line: str) -> str:
    return "q:" + hashlib.sha1(f"{rel}\n{line.strip()}".encode("utf-8")).hexdigest()[:12]


def _shown(line: str) -> str:
    """The fact as the owner reads it: without the bullet, the source mark and the day it was written."""
    t = line.strip().lstrip("-* ").strip()
    t = _SRC.sub("", t) if " · " in t else t
    return _TAIL.sub("", t).strip()


def quiz_facts(vault: Vault) -> list[dict]:
    items = []
    for n in _quiz_notes(vault):
        raw = vault.read_raw(n.rel) or ""
        for line in raw.splitlines():
            if not line.lstrip().startswith(("- ", "* ")):
                continue
            text = _shown(line)
            if 12 <= len(text) <= 240 and not text.lower().startswith("статус:"):
                items.append({"id": _qid(n.rel, line), "text": text, "where": n.rel, "title": n.title})
    return items


def quiz(vault: Vault, size: int = QUIZ_SIZE) -> dict:
    facts = quiz_facts(vault)
    facts.sort(key=lambda f: (len(f["text"]), f["where"]))  # simple first: short facts before long ones
    picked, seen = [], set()
    for f in facts:  # different notes first: a quiz about one card is dull
        if f["where"] not in seen:
            picked.append(f)
            seen.add(f["where"])
        if len(picked) >= size:
            break
    for f in facts:
        if len(picked) >= size:
            break
        if f not in picked:
            picked.append(f)
    return {"items": picked, "total": len(facts)}


@locked
def quiz_answer(vault: Vault, item_id: str, verdict: str, text: str = "", today: dt.date | None = None) -> dict:
    """yes — still true (a dated status moves to today); changed — the new wording replaces it, the old line goes to
    the fact archive; no — it was never true: removed to the fact archive."""
    from .memory import _archive_lines, add_event, generate_now, ru_date

    it = next((x for x in quiz_facts(vault) if x["id"] == item_id), None)
    if not it:
        raise KeyError("этого факта уже нет — память изменилась")
    rel = it["where"]
    lines = (vault.read_raw(rel) or "").splitlines()
    idx = next((i for i, x in enumerate(lines) if _qid(rel, x) == item_id), None)
    if idx is None:
        raise KeyError("строка уже изменилась")
    old = lines[idx]
    if verdict == "yes":
        stamp = f"(статус {ru_date(today)})"
        new = re.sub(r"\((?:статус|status)\s+[^)]*\)", stamp, old, flags=re.I)
        if new == old:
            return {"ok": True, "changed": False}
        lines[idx] = new
        summary = f"подтверждено в квизе: {it['text'][:100]}"
    elif verdict == "changed":
        fact = " ".join(text.split())
        if not fact:
            raise ValueError("напиши, как теперь")
        lines[idx] = f"- {fact} ({ru_date(today)})"
        summary = f"поправлено в квизе: {fact[:100]}"
    elif verdict == "no":
        lines.pop(idx)
        summary = f"неправда, убрано в квизе: {it['text'][:100]}"
    else:
        raise ValueError("неизвестный ответ")
    ev = write_with_journal(vault, "owner", rel, "\n".join(lines) + "\n", summary)
    if verdict != "yes":
        _archive_lines(vault, rel, [old], "поправлено владельцем" if verdict == "changed" else "неправда", today)
        add_event(vault, f"{it['title']}: {summary}", today)
    generate_now(vault, today)
    return {"ok": True, "changed": True, "event": ev.get("id", "") if isinstance(ev, dict) else ""}


# ---------------------------------------------------------------- the interview

INTERVIEW = [
    ("who", "Как тебя зовут и чем ты занимаешься?", "Анна, продакт-менеджер в финтехе, веду мобильное приложение"),
    ("where", "Где живёшь?", "Лиссабон"),
    ("focus", "Что сейчас главное? Можно несколько через запятую", "запуск пилота, найм дизайнера"),
    ("projects", "Над какими проектами работаешь? Через запятую", "Пилот, Сайт компании"),
    (
        "people",
        "Кто важные люди вокруг? «Имя — кто это», через точку с запятой",
        "Олег — сооснователь; Мария — дизайнер",
    ),
    ("style", "Как с тобой говорить ИИ?", "коротко, на ты, без воды"),
    ("never", "Чего ИИ делать не должен? Через точку с запятой", "не выдумывать цифры; не писать длинные вступления"),
]


def _items(s: str, sep: str = ",") -> list[str]:
    return [x.strip() for x in re.split(rf"[{re.escape(sep)};\n]", s or "") if x.strip()]


def interview_save(vault: Vault, answers: dict) -> dict:
    """The answers as ordinary facts: added to the memory, nothing that is there is overwritten."""
    from .memory import remember

    a = {k: " ".join(str(answers.get(k) or "").split()) for k, _, _ in INTERVIEW}
    saved = 0

    def put(fact: str, where: str) -> None:
        nonlocal saved
        if fact.strip():
            remember(vault, fact, where, "owner")
            saved += 1

    put(a["who"], "profile:Кто я")
    if a["where"]:
        put(f"Живу: {a['where']}", "profile:Кто я")
    for x in _items(a["focus"]):
        put(x, "profile:Сейчас главное")
    for x in _items(a["projects"]):
        put("Проект в работе", f"project:{x[:80]}")
    for x in _items(a["people"], ";"):
        name, sep, who = x.partition("—") if "—" in x else x.partition(" - ")
        if name.strip():
            put(who.strip() or "важный человек", f"person:{name.strip()[:60]}")
    if a["style"]:
        put(f"Как со мной говорить: {a['style']}", "rules")
    for x in _items(a["never"], ";"):
        put(f"Нельзя: {x}", "rules")
    return {"ok": True, "facts": saved}
