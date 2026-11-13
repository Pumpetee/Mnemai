"""Recipes of tasks («рецепты задач», a prompt underneath) — the way the owner works in Obsidian: a task that comes
back gets its own prompt. The interface says «рецепт», not «промт»: clearer for people who don't write prompts.

When a request looks like a task the owner already gave before (the second similar request — or every task, as set),
Mnemai doesn't do it straight away. It asks first: "I'll write a prompt so next time you don't explain it again and
don't spend tokens on clarifications". Only with consent:
  write     — a model writes the prompt (goal, input, steps, result format, checks), it is saved as a Markdown file in
              the memory folder «90 System/Recipes/», then the task is done by it;
  just do   — the task is done as usual;
  never     — not offered again for requests like this one.
Next time a matching request comes, the prompt is used automatically and the answer says so.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

from ..retrieve import STOP, stem
from ..vault import Vault

from ..vault import OLD_PROMPTS, PROMPTS as FOLDER

TASK_VERBS = set(
    stem(w)
    for w in """напиши написать составь составить сделай сделать подготовь подготовить переведи перевести
разбери разобрать проанализируй проанализировать оформи оформить сократи сократить перепиши переписать создай создать
придумай придумать посчитай посчитать проверь проверить найди найти собери собрать сравни сравнить опиши описать
сформулируй сформулировать отредактируй отредактировать структурируй резюмируй суммируй выпиши подбери распиши
write draft make prepare translate analyze analyse summarize summarise rewrite create compose check find compare
format edit list plan""".split()
)
_WORD = re.compile(r"[\wё]+", re.I)


def terms(text: str) -> set[str]:
    return {stem(w) for w in _WORD.findall(text) if w.lower() not in STOP and len(w) > 2}


def is_task(text: str) -> bool:
    words = _WORD.findall(text)
    return len(words) >= 4 and any(stem(w) in TASK_VERBS for w in words[:12])


def sim(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    common = len(a & b)
    return 0.0 if common < 2 else common / min(len(a), len(b))


# ---------------------------------------------------------------- the prompt files


def folder(vault: Vault) -> Path:
    d = vault.root / FOLDER
    old = vault.root / OLD_PROMPTS
    if old.is_dir() and not d.exists():  # memory from before 0.5.3: the folder is renamed once
        old.rename(d)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _parse(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    meta, body = {}, raw
    if raw.startswith("---"):
        head, _, body = raw[3:].partition("\n---")
        for line in head.strip().splitlines():
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
        body = body.lstrip("\n")
    examples = meta.get("examples", "")
    try:
        examples = json.loads(examples) if examples else []
    except ValueError:
        examples = [examples]
    return {
        "file": path.name,
        "name": meta.get("name") or path.stem,
        "when": meta.get("when", ""),
        "examples": examples,
        "uses": int(meta.get("uses") or 0),
        "created": meta.get("created", ""),
        "last_used": meta.get("last_used", ""),
        "body": body.strip(),
    }


def _write(vault: Vault, p: dict) -> Path:
    path = folder(vault) / p["file"]
    head = "\n".join(
        [
            f"name: {p['name']}",
            f"when: {p['when']}",
            f"examples: {json.dumps(p['examples'][-5:], ensure_ascii=False)}",
            f"uses: {p['uses']}",
            f"created: {p['created']}",
            f"last_used: {p.get('last_used', '')}",
        ]
    )
    path.write_text(f"---\n{head}\n---\n\n{p['body']}\n", encoding="utf-8")
    return path


def all_prompts(vault: Vault) -> list[dict]:
    d = vault.root / FOLDER
    return sorted((_parse(f) for f in d.glob("*.md")), key=lambda p: (-p["uses"], p["name"])) if d.exists() else []


def delete(vault: Vault, file: str) -> None:
    path = folder(vault) / Path(file).name
    if path.exists():
        path.unlink()


def slug(name: str) -> str:
    s = re.sub(r'[\\/:*?"<>|\n\r\t]+', " ", name).strip()[:60] or "Рецепт"
    return s + ".md"


def save(vault: Vault, name: str, when: str, body: str, example: str) -> dict:
    file = slug(name)
    i = 2
    while (folder(vault) / file).exists():
        file = slug(f"{name} {i}")
        i += 1
    p = {
        "file": file,
        "name": name,
        "when": when,
        "examples": [example],
        "uses": 0,
        "created": dt.date.today().isoformat(),
        "last_used": "",
        "body": body,
    }
    _write(vault, p)
    from .. import achievements as ACH

    ACH.event(vault, "prompts")
    return p


def used(vault: Vault, p: dict, request: str) -> None:
    p = dict(p)
    p["uses"] += 1
    p["last_used"] = dt.date.today().isoformat()
    if request not in p["examples"]:
        p["examples"] = (p["examples"] + [request])[-5:]
    _write(vault, p)


# ---------------------------------------------------------------- deciding


def settings(vault: Vault) -> dict:
    from ..agent import profile as P

    prof = P.load(vault)
    return {
        "mode": prof.get("prompts_mode", "second"),
        "auto": prof.get("prompts_auto", True),
        "never": prof.get("prompts_never", []),
    }


def match(vault: Vault, text: str) -> dict | None:
    """A saved prompt for this request, if there is one."""
    q = terms(text)
    best, score = None, 0.0
    for p in all_prompts(vault):
        s = max([sim(q, terms(p["name"] + " " + p["when"]))] + [sim(q, terms(e)) for e in p["examples"]])
        if s > score:
            best, score = p, s
    return best if score >= 0.6 else None


def _read(f: Path) -> dict | None:
    """Windows holds a file for a moment while another thread saves it: try again a few times."""
    import time

    for _ in range(10):
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except (PermissionError, ValueError):
            time.sleep(0.05)
        except OSError:
            return None
    return None


def similar_before(vault: Vault, text: str, chat_id: str, msg_index: int) -> str:
    """An earlier request of the owner that looks like this one AND got an answer ("" — none).

    A request that failed or was never answered is not an example of "how it was done": offering a recipe for it
    would mean recording "do it without explaining and without questions" for a task nobody has done yet."""
    from .engine import _dir

    q = terms(text)

    def mtime(x: Path) -> float:
        try:
            return x.stat().st_mtime
        except OSError:
            return 0.0

    for f in sorted(_dir(vault).glob("*.json"), key=mtime, reverse=True)[:200]:
        c = _read(f)
        if c is None:
            continue
        msgs = c.get("messages", [])
        for i, m in enumerate(msgs):
            if m.get("role") != "user" or (c["id"] == chat_id and i >= msg_index):
                continue
            answered = any(
                later.get("role") == "assistant" and later.get("kind") not in ("prompt_offer", "self_ask") and later.get("text")
                for later in msgs[i + 1 :]
            )
            if not answered:
                continue  # it never got an answer: not a recipe yet
            if sim(q, terms(m.get("text", ""))) >= 0.6:
                return m["text"]
    return ""


def decide(vault: Vault, chat: dict, text: str) -> dict:
    """{"use": prompt} | {"offer": earlier request or ""} | {}."""
    st = settings(vault)
    if st["mode"] == "off" or chat.get("consortium"):
        return {}
    if st["auto"]:
        p = match(vault, text)
        if p:
            return {"use": p}
    if not is_task(text):
        return {}
    q = terms(text)
    if any(sim(q, set(sig)) >= 0.6 for sig in st["never"]):
        return {}
    if st["mode"] == "every":
        return {"offer": ""}
    before = similar_before(vault, text, chat["id"], len(chat["messages"]) - 1)
    return {"offer": before} if before else {}


def never(vault: Vault, text: str) -> None:
    from ..agent import profile as P

    sig = sorted(terms(text))[:12]
    P.save(vault, {"prompts_never": (P.load(vault).get("prompts_never", []) + [sig])[-100:]})


WRITER = """Ты пишешь промт — инструкцию для ИИ на повторяющуюся задачу владельца, чтобы в следующий раз её не объяснять.
Не выполняй саму задачу. Опиши, как её делать хорошо именно для этого владельца, с учётом его правил и памяти.

Запросы владельца на эту задачу:
{examples}

Промт должен содержать: цель; что бывает на входе; шаги; формат результата; проверки перед сдачей; чего не делать.
Коротко и конкретно, без воды. Пиши на том же языке, что и запросы.

Верни строго в таком виде:
НАЗВАНИЕ: 2–5 слов
КОГДА: одна строка — на какие запросы этот промт
ПРОМТ:
текст промта"""


def parse_written(text: str, fallback_name: str) -> tuple[str, str, str]:
    name = re.search(r"НАЗВАНИЕ\s*:\s*(.+)", text)
    when = re.search(r"КОГДА\s*:\s*(.+)", text)
    body = re.split(r"ПРОМТ\s*:\s*", text, maxsplit=1)
    return (
        (name.group(1).strip(" *«»\"") if name else fallback_name)[:60],
        (when.group(1).strip() if when else "")[:200],
        (body[1] if len(body) > 1 else text).strip(),
    )


def block(p: dict) -> str:
    return f"=== Промт владельца на эту задачу: «{p['name']}» ===\n{p['body']}\n=== Выполни задачу по этому промту ==="
