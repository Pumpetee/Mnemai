"""The wrapper chat: the owner talks to any model, memory and his rules are applied, Mnemai learns as he writes.

Flow of one message:
  1. saved to the chat; learning on it starts at once in the background (live feed shows "читаю → поняла → …");
  2. system prompt = how to work with him (behavior profile) + memory this model may see + the extra memory folders;
  3. the answer streams; with "второй проход" on, a second call checks the draft against the rules and fixes it;
  4. a ```ask block in the answer becomes a question with buttons.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import secrets
import threading
import time
from pathlib import Path

from ..agent import profile as P
from ..learn import engine as learn
from ..learn.sources import Episode
from ..memory import context_for, ru_date
from ..vault import Vault
from . import providers as PR
from .attach import save as save_files


HOWTO_RE = re.compile(
    r"подключ|chatgpt|чатгпт|gpt|claude|клод|gemini|джемин|openrouter|ollama|ключ|api|расширени|другие ии|другим ии",
    re.I,
)
_gen: dict[str, dict] = {}

ASK_RULE = """Вопросы владельцу:
Встречный вопрос задавай только тогда, когда без ответа задачу нельзя выполнить или понять её можно по-разному так,
что результат выйдет разным. Факт, мнение, решение или просьбу владельца не превращай в вопрос: принял — продолжай.
Не хватает данных, но можно разумно допустить — сделай с допущением и назови его одной фразой, а не спрашивай.
Вопросов не больше одного на ответ, и после ответа владельца делай, а не уточняй снова. Вопрос — блоком (2–4 коротких
варианта), после блока ничего не пиши:
```ask
{"question": "Текст вопроса?", "options": ["Вариант 1", "Вариант 2"]}
```
Владелец ответит выбором или своими словами."""

# with "Пояснять варианты": why the question is asked, and what each option leads to
ASK_RULE_HINTS = """Вопросы владельцу:
Встречный вопрос задавай только тогда, когда без ответа задачу нельзя выполнить или понять её можно по-разному так,
что результат выйдет разным. Факт, мнение, решение или просьбу владельца не превращай в вопрос: принял — продолжай.
Не хватает данных, но можно разумно допустить — сделай с допущением и назови его одной фразой, а не спрашивай.
Вопросов не больше одного на ответ, и после ответа владельца делай, а не уточняй снова. Вопрос — блоком (2–4 варианта),
после блока ничего не пиши:
```ask
{"question": "Текст вопроса?", "why": "Зачем спрашиваю — одной короткой фразой",
 "options": [{"label": "Вариант 1", "hint": "что будет, если выбрать, — до 8 слов"},
             {"label": "Вариант 2", "hint": "…"}]}
```
label — 1–4 слова, hint — коротко и по делу, без повтора label. Каждый вариант — объект с label и hint, даже если
раньше в разговоре варианты были без пояснений. Варианты — в том порядке, в каком их стоит рассматривать.
Владелец ответит выбором или своими словами."""


def _dir(vault: Vault) -> Path:
    d = vault.service / "chats"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _hidden(g: dict) -> dict:
    """What stayed on the computer for this answer: secrets cut from the request and from the search query."""
    out = dict((g.get("usage") or {}).get("redacted") or {})
    for k, v in (g.get("web_hid") or {}).items():
        out[k] = out.get(k, 0) + v
    return out


def _read(f: Path) -> str:
    """Windows refuses a read for a moment while save_chat swaps the file in: wait for it, like the writer does."""
    for _ in range(20):
        try:
            return f.read_text(encoding="utf-8")
        except PermissionError:
            time.sleep(0.05)
    return f.read_text(encoding="utf-8")


def load_chat(vault: Vault, cid: str) -> dict:
    if not re.fullmatch(r"[a-f0-9]{8,16}", cid or ""):
        raise KeyError("нет такого чата")
    f = _dir(vault) / f"{cid}.json"
    if not f.exists():
        raise KeyError("нет такого чата")
    return json.loads(_read(f))


_locks: dict[str, threading.RLock] = {}
_locks_guard = threading.Lock()


def chat_lock(cid: str) -> threading.RLock:
    """One writer per chat: the answer, the background title and the owner's edits never overwrite each other."""
    with _locks_guard:
        return _locks.setdefault(cid, threading.RLock())


def save_chat(vault: Vault, chat: dict) -> None:
    f = _dir(vault) / f"{chat['id']}.json"
    tmp = f.with_name(f"{f.stem}.{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(chat, ensure_ascii=False, indent=1), encoding="utf-8")
    for attempt in range(20):
        try:
            tmp.replace(f)
            return
        except PermissionError:  # Windows: a reader holds the file for a moment
            time.sleep(0.05)
    tmp.replace(f)


def modify_chat(vault: Vault, cid: str, fn) -> dict:
    """Re-read the chat from disk, change it, save — all under the chat's lock."""
    with chat_lock(cid):
        chat = load_chat(vault, cid)
        fn(chat)
        save_chat(vault, chat)
        return chat


def _session_file(vault: Vault) -> Path:
    return vault.service / "session.json"


def current_session(vault: Vault) -> dict:
    """The session new conversations join: {"id", "started"}. The first one starts on first use."""
    try:
        s = json.loads(_read(_session_file(vault)))
        if re.fullmatch(r"[a-f0-9]{8}", str(s.get("id", ""))):
            return s
    except (OSError, ValueError):
        pass
    return new_session(vault)


def new_session(vault: Vault) -> dict:
    """«Новая сессия»: the conversations started from now on form a new group in the list. Every conversation sends
    the model only its own messages, so a new session starts with a clean context — memory and rules, no history."""
    s = {"id": secrets.token_hex(4), "started": _now()}
    vault.service.mkdir(parents=True, exist_ok=True)
    from ..fsutil import write_json

    write_json(_session_file(vault), s)
    return s


def _names_file(vault: Vault) -> Path:
    return vault.service / "session_names.json"


def session_names(vault: Vault) -> dict:
    """The names the owner gave his sessions: {session id: name}."""
    try:
        d = json.loads(_read(_names_file(vault)))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def rename_session(vault: Vault, sid: str, name: str) -> dict:
    from ..fsutil import write_json

    names = session_names(vault)
    name = (name or "").strip()[:60]
    if name:
        names[sid] = name
    else:
        names.pop(sid, None)  # an empty name: back to «Сессия»
    vault.service.mkdir(parents=True, exist_ok=True)
    write_json(_names_file(vault), names)
    return names


def delete_session(vault: Vault, sid: str) -> int:
    """Delete every conversation of a session («old» — those started before sessions existed). Pinned ones stay."""
    n = 0
    for c in list_chats(vault, limit=100000):
        if (c.get("session") or "old") == sid and not c.get("pinned"):
            delete_chat(vault, c["id"])
            n += 1
    names = session_names(vault)
    if sid in names:
        rename_session(vault, sid, "")
    return n


def list_chats(vault: Vault, limit: int = 200, q: str = "", sort: str = "date") -> list[dict]:
    """Pinned first, then by last activity. q searches titles and messages."""
    out = []
    ql = (q or "").strip().lower()
    for f in _dir(vault).glob("*.json"):
        try:
            c = json.loads(_read(f))
        except (ValueError, OSError):  # half-written or gone meanwhile: the next refresh shows it
            continue
        hit = ""
        if ql:
            if ql in c.get("title", "").lower():
                hit = c.get("title", "")
            else:
                m = next((m["text"] for m in c.get("messages", []) if ql in m.get("text", "").lower()), None)
                if m is None:
                    continue
                i = m.lower().index(ql)
                hit = "…" + m[max(0, i - 30) : i + 60].replace("\n", " ") + "…"
        out.append(
            {
                "id": c["id"],
                "title": c.get("title", ""),
                "updated": c.get("updated", ""),
                "model": c.get("model", ""),
                "pinned": bool(c.get("pinned")),
                "private": bool(c.get("private")),
                "session": c.get("session", ""),
                "created": c.get("created", ""),
                "hit": hit,
                "count": len(c.get("messages", [])),
                "tokens": chat_tokens(c),
                "saved": sum(int(m.get("saved") or 0) for m in c.get("messages", [])),
            }
        )
    if sort == "tokens":
        out.sort(key=lambda c: c["tokens"], reverse=True)
    else:
        out.sort(key=lambda c: c["updated"], reverse=True)
    out.sort(key=lambda c: not c["pinned"])
    return out[:limit]


def chat_tokens(chat: dict) -> int:
    """Everything the provider processed for this chat: prompts with memory, cache, answers, titles."""
    t = sum(sum((m.get("tokens") or {}).values()) for m in chat.get("messages", []))
    return t + sum((chat.get("title_tokens") or {}).values())


def update_chat(
    vault: Vault,
    cid: str,
    title: str | None = None,
    pinned: bool | None = None,
    private: bool | None = None,
    consortium: dict | None = None,
) -> dict:
    from . import consortium as CO

    def change(chat):
        if consortium is not None and chat.get("consortium"):
            chat["consortium"] = CO.clean({**chat["consortium"], **consortium})
        if title is not None and title.strip():
            chat["title"] = " ".join(title.split())[:80]
            chat["title_manual"] = True  # the owner named it — never rename automatically
        if pinned is not None:
            chat["pinned"] = bool(pinned)
        if private is not None:
            chat["private"] = bool(private)  # "не учиться на этом разговоре"

    chat = modify_chat(vault, cid, change)
    return {k: chat.get(k) for k in ("id", "title", "pinned", "private", "consortium")}


def export_chat(vault: Vault, cid: str) -> str:
    chat = load_chat(vault, cid)
    out = [f"# {chat.get('title', 'Разговор')}", ""]
    for m in chat["messages"]:
        if m.get("hidden") or not m.get("text"):
            continue
        who = "Я" if m["role"] == "user" else "Mnemai"
        out += [f"**{who}** · {m.get('ts', '').replace('T', ' ')[:16]}", "", m["text"], ""]
    return "\n".join(out)


def delete_chat(vault: Vault, cid: str) -> None:
    load_chat(vault, cid)
    (_dir(vault) / f"{cid}.json").unlink()


def default_model(vault: Vault) -> str:
    prof = P.load(vault)
    last = prof.get("last_model") or ""  # the model the owner picked last wins, if it is still available
    pid, _, mid = last.partition(":")
    if last and any(
        p["id"] == pid and p["ready"] and (not mid or any(m["id"] == mid for m in p["models"]))
        for p in PR.status(vault)
    ):
        return last
    st = PR.status(vault)
    pick = prof.get("default_model") or ""
    if pick and any(p["id"] == pick.partition(":")[0] and p["ready"] for p in st):
        return pick  # the default only while its AI works: switched off or out of money — the next one answers
    for p in st:
        if p["ready"] and p["models"]:
            return f"{p['id']}:{p['models'][0]['id']}"
    return ""  # nothing connected yet: the chat says so instead of pretending Claude is there


NO_MODEL = "Сначала выбери, с каким ИИ говорить: скачай бесплатную модель на компьютер или укажи ключ — Настройки → ИИ и модели."


def split_model(ref: str) -> tuple[str, str]:
    pid, _, model = (ref or "").partition(":")
    if pid not in PR.PROVIDERS:
        raise ValueError(NO_MODEL)
    return pid, model


# ---------------------------------------------------------------- prompt


LANGS = ["ru", "en", "zh", "es", "hi", "pt", "fr", "de", "ja"]
LANG_NAMES = {
    "ru": "русский",
    "en": "английский (English)",
    "zh": "китайский (简体中文)",
    "es": "испанский (Español)",
    "hi": "хинди (हिन्दी)",
    "pt": "португальский (Português)",
    "fr": "французский (Français)",
    "de": "немецкий (Deutsch)",
    "ja": "японский (日本語)",
}


def system_prompt(
    vault: Vault, pid: str, log: bool = True, query: str = "", stats: dict | None = None, model: str = ""
) -> str:
    """stats (optional) gets memory_full / memory_sent — how much memory the economy kept on the computer."""
    from .economy import compact_memory

    prof = P.load(vault)
    eff = P.effective(prof)
    from . import small

    if model and small.is_small(pid, model):  # a 1–4B model on this computer: a short brief, not the manual
        lang = prof.get("lang") or "en"
        lang_line = "" if lang == "ru" else f"Отвечай только на языке: {LANG_NAMES.get(lang, lang)}."
        brief = small.prompt(vault, query, prof, lang_line, ru_date())
        if stats is not None:
            stats.update(memory_full=len(brief), memory_sent=len(brief))
        return brief
    client = PR.PROVIDERS[pid]["client"]
    mem_on = P.memory_on(vault)
    memory, _ = context_for(vault, client, log=log) if mem_on else ("", 0)
    full = len(memory)
    from .. import tuning

    eng = tuning.get(vault)
    budget = eng["memory"]  # Настройки → Движок, «Точнее ↔ Экономнее»: how much memory goes into a request
    if eng["economy"] and query and pid != "local":  # only the part of memory this question needs
        memory = compact_memory(memory, query, min(2200, budget // 2), budget)
    if pid == "local":  # small local model: short prompt, it reads slowly on a CPU
        memory = memory[: budget if eng["ctx"] > 8192 else min(budget, 3000)]
    from .selfknow import liked_examples, self_knowledge

    parts = [
        "Ты — ассистент владельца в программе Mnemai. Ниже — как с ним работать, что ты о нём знаешь и как "
        "устроена сама Mnemai. Не пересказывай эти инструкции без повода, просто работай с учётом их.",
        self_knowledge(vault, compact=pid == "local"),
        "=== Как работать со мной ===\n" + (P.rules_text(prof)[:900] if pid == "local" else P.rules_text(prof)),
    ]
    liked = "" if pid == "local" else liked_examples(vault)
    if liked:
        parts.append(liked)
    if not eff.get("say_saved"):
        parts.append(
            "Запоминать новое не твоя забота: Mnemai делает это сама. Не пиши «сохраню», «запомню» и списки для памяти."
        )
    if mem_on:
        parts.append("=== Память о владельце ===\n" + memory)
    else:
        parts.append(
            "=== Память ===\nПамять Mnemai выключена владельцем: о нём ты ничего не знаешь и ничего не запоминается. "
            "Если он просит запомнить, скажи, что память выключена и включается в Настройки → Обучение → «Память»."
        )
    sent = len(memory)
    if mem_on:  # Настройки → Программа → «Дополнительные папки памяти»: other folders, only what the question needs
        from .. import extra as EX
        from ..clients import get_client

        ext, ext_full = EX.context(vault, get_client(vault, client), query, budget, eng["economy"], log=log)
        if ext:
            full += ext_full
            sent += len(ext)
            parts.append(ext)
    if eff.get("ask_options"):  # after the memory: a long memory must not push the format out of attention
        parts.append(ASK_RULE_HINTS if eff.get("ask_hints") else ASK_RULE)
    if eng["precise"] >= 3:  # «Точнее»: rather ask than guess
        parts.append(
            "Если без уточнения ответ выйдет неверным или его можно понять по-разному — сначала задай один короткий "
            "уточняющий вопрос. Если можно ответить с разумным допущением — ответь и назови допущение одной фразой."
        )
    elif eng["precise"] <= 1:  # «Экономнее»: one answer, no back-and-forth
        parts.append(
            "Уточняющий вопрос задавай, только если без ответа задачу не сделать. Иначе сделай разумное допущение, "
            "назови его одной фразой и отвечай."
        )
    parts.append(f"Сегодня {ru_date()}.")
    from .selfknow import MANUAL, about_mnema, kb_for

    if about_mnema(query):  # a question about the program: its map and knowledge base
        parts.append(MANUAL)
        kb = kb_for(query)
        if kb:
            parts.append(kb)
    lang = prof.get("lang") or "en"
    # the language chosen on the first screen (or with the language button): always that one, whatever he wrote in
    parts.append(
        f"Язык ответов: {LANG_NAMES.get(lang, lang)}. Отвечай владельцу только на этом языке, даже если он написал "
        "на другом и даже если память и правила написаны на другом языке. Сменить язык он может кнопкой языка в Mnemai."
    )
    if stats is not None:
        stats.update(memory_full=full, memory_sent=sent)
    return "\n\n".join(parts)


SECOND_PASS = """Ты — редактор ответов. Проверь черновик ответа ассистента владельцу по правилам ниже и по памяти.
Исправь всё, что нарушает правила: форму, длину, выдуманные факты и цифры, противоречия памяти, штампы, лишнее.
Если всё в порядке — верни черновик без изменений. Верни ТОЛЬКО финальный текст ответа, без пояснений.

ПРАВИЛА:
{rules}

ПАМЯТЬ (для сверки фактов):
{memory}"""


# ---------------------------------------------------------------- send

TOOL_MARKUP = re.compile(
    r"<(function_calls|invoke|antml:invoke)\b.*?(</\1>|$)|</?(parameter|function_calls)\b[^>]*>", re.S
)


def strip_thinking(text: str) -> str:
    """Thinking models write their reasoning before the answer. The owner sees only the answer."""
    if "</think>" in text:
        return text.rsplit("</think>", 1)[1].lstrip()
    if text.lstrip().startswith("<think>"):
        return ""
    return text


def strip_tool_markup(text: str) -> str:
    """A model without tools sometimes types a tool call as text. The owner never needs to see it."""
    if "<" not in text:
        return text
    return re.sub(r"\n{3,}", "\n\n", TOOL_MARKUP.sub("", text)).strip()


def _phase(g: dict) -> str:
    """What the owner sees while there are no words yet — what exactly is going on and how long it has been going on."""
    elapsed = int(time.time() - g.get("started", time.time()))
    if g["phase"] != "пишу" or strip_thinking(g["text"]).strip():
        phase = g["phase"]
        if phase.startswith("делаю:") and elapsed >= 5:
            return f"{phase} · {elapsed} с"
        if phase == "думаю" and elapsed >= 5:
            return f"модель думает · {elapsed} с"
        return phase
    if g.get("pid") != "local":  # a plain chat: who speaks matters only in a consortium
        if not g.get("consortium") and elapsed < 5:
            return ""
        who = g.get("who") or "модель"
        tail = " · можно остановить" if elapsed >= 60 else f" · {elapsed} с" if elapsed >= 5 else ""
        return f"{who} думает{tail}"
    if (g.get("usage") or {}).get("reasoning") or g["text"].lstrip().startswith("<think>"):
        return "модель рассуждает, потом ответит"
    pr = (g.get("usage") or {}).get("progress")
    what = "читает вопрос и найденное" if g.get("sources") else "читает вопрос и память"
    if not pr or pr["part"] <= 0:
        return f"модель на компьютере {what}"
    if pr["part"] >= 1:
        return "модель прочитала, начинает писать"
    pct = int(pr["part"] * 100)
    if pct < 1:
        return f"модель на компьютере {what}"
    left = ""
    if pr["done"] > 0 and pr["ms"] > 3000:
        sec = (pr["total"] - pr["done"]) * pr["ms"] / pr["done"] / 1000
        left = f" · ещё около {int(sec // 60)} мин" if sec >= 90 else f" · ещё около {max(5, int(sec / 5) * 5)} с"
    return f"модель на компьютере {what} · {pct}%{left}"


def state(cid: str) -> dict:
    g = _gen.get(cid)
    from .terms import visible

    if g and g.get("consortium"):
        return {
            "text": visible(strip_tool_markup(strip_thinking(g["text"]))),
            "done": g["done"],
            "error": g["error"],
            "phase": _phase(g),
            "speaker": g.get("speaker", ""),
            "seq": g.get("seq", 0),
            "turn": g.get("turn", 0),
            "turns": g.get("turns", 0),
            "status": g.get("status", ""),
            "round": g.get("round", 0),
            "rounds": g.get("rounds", 0),
            "members": g.get("members", []),
            "idx": g.get("idx", 0),
            "next": g.get("next", ""),
            "pausing": bool(g.get("pause")),
            "finishing": bool(g.get("finish")),
        }
    return (
        {
            "text": visible(strip_tool_markup(strip_thinking(g["text"]))).split("```mnema")[0].rstrip(),
            "done": g["done"],
            "error": g["error"],
            "phase": _phase(g),
            **({"pending": g["pending"]} if g.get("pending") else {}),
        }
        if g
        else {"text": "", "done": True, "error": "", "phase": ""}
    )


def _add_msg(vault: Vault, cid: str, msg: dict) -> None:
    def add(c):
        c["messages"].append(msg)
        c["updated"] = _now()

    try:
        modify_chat(vault, cid, add)
    except KeyError:
        pass


_answers: dict[str, dict] = {}


def _act(vault: Vault, cid: str, g: dict, call: dict, client: str, model: str) -> str | None:
    """One action the model asked for: the owner's word (unless already given for this conversation), then the deed.
    Returns what the model is told; None if the owner stopped the answer meanwhile."""
    from . import tools as TL

    try:
        desc = TL.what(vault, call)
    except Exception as e:
        return f"Не сделано: {e}"
    allowed = not P.load(vault).get("tools_ask", False) or call["tool"] in (load_chat(vault, cid).get("tools_ok") or [])
    if not allowed:
        aid = secrets.token_hex(4)
        box = {"event": threading.Event(), "choice": ""}
        _answers[aid] = box
        g.update(
            pending={"id": aid, "tool": call["tool"], "what": desc, "write": call["tool"] in TL.WRITES},
            phase="жду твоего разрешения",
        )
        while not box["event"].wait(0.3):
            if g["stop"]:
                g.pop("pending", None)
                _answers.pop(aid, None)
                return None
        g.pop("pending", None)
        _answers.pop(aid, None)
        choice = box["choice"]
        if choice == "no":
            _add_msg(
                vault,
                cid,
                {"role": "assistant", "kind": "action", "ts": _now(), "text": "Не разрешено: " + desc, "refused": True},
            )
            return "Владелец не разрешил это действие. Не повторяй его; ответь без него или спроси, как быть."
        if choice == "always":
            modify_chat(
                vault, cid, lambda c: c.__setitem__("tools_ok", sorted(set(c.get("tools_ok") or []) | {call["tool"]}))
            )
    g["phase"] = "делаю: " + desc
    try:
        from .. import mcp_server as MC

        result, line, path = MC.run_action(vault, call, client)
    except Exception as e:
        _add_msg(
            vault,
            cid,
            {"role": "assistant", "kind": "action", "ts": _now(), "text": f"Не получилось {desc}: {e}", "failed": True},
        )
        return f"Не получилось: {e}"
    _add_msg(
        vault,
        cid,
        {"role": "assistant", "kind": "action", "ts": _now(), "text": line, **({"path": path} if path else {})},
    )
    from .. import achievements as ACH

    ACH.event(vault, "action", tool=call["tool"])
    return result


def answer_action(cid: str, aid: str, choice: str) -> dict:
    """The owner's word on an action: yes | no | always (yes for this conversation)."""
    box = _answers.get(aid)
    if not box:
        raise ValueError("это действие уже не ждёт ответа")
    box["choice"] = choice if choice in ("yes", "no", "always") else "no"
    box["event"].set()
    return {"ok": True}


def stop(cid: str) -> None:
    g = _gen.get(cid)
    if not g:
        return
    g["stop"] = True
    if not g.get("consortium") and not g.get("done") and not strip_thinking(g.get("text", "")).strip():
        # nothing came yet and the request may wait a long time: the conversation is free right now,
        # whatever arrives later is dropped
        g.update(abandoned=True, done=True, phase="", error="")


OPENER = (
    "[Владелец нажал «Пусть Mnemai начнёт сама» и ждёт, что ты заговоришь первым.]\n"
    "Начни разговор сам, коротко, в 2–4 строки. Поздоровайся, по имени, если знаешь его. Опираясь на память, "
    "предложи одно-два конкретных дела, с которых можно начать прямо сейчас: продолжить проект, проверить "
    "устаревший статус, разобрать входящие, вернуться к недавнему решению. Если памяти почти нет — предложи "
    "познакомиться и задай один простой вопрос о том, чем он занимается. Ничего не выдумывай о нём. У фактов в "
    "памяти стоят даты: событие называй сегодняшним или недавним, только если так говорит его дата, а решение старше "
    "месяца предлагай проверить, а не выдавай за новость. Закончи "
    "одним вопросом. Не упоминай эту просьбу."
)


def send(
    vault: Vault,
    text: str,
    cid: str = "",
    model: str = "",
    sync: bool = False,
    files: list | None = None,
    quote: str = "",
    learn: bool = True,
    web: bool | None = None,
    consortium: dict | None = None,
    terms: bool | None = None,
    opener: bool = False,
    private: bool | None = None,
) -> dict:
    """web: search the internet for this message (None — the composer switch saved in settings).
    private: «Без обучения» for a new conversation — set before its first message is learned from.
    consortium: {"members": [model refs], "rounds": n} — start a discussion of several AIs in a new chat."""
    from . import consortium as CO

    text = (text or "").strip()
    if opener:  # Mnemai speaks first: the request itself stays hidden
        text, learn, files, quote = OPENER, False, None, ""
    if not text and not files:
        raise ValueError("пустое сообщение")
    text = text or "Посмотри прикреплённое."
    if cid:
        chat = load_chat(vault, cid)
    else:
        chat = {
            "id": secrets.token_hex(6),
            "title": "Новый разговор" if opener else " ".join(text.split())[:60],
            "created": _now(),
            "session": current_session(vault)["id"],
            "messages": [],
        }
        if consortium:
            chat["consortium"] = CO.clean(consortium)
        if private:
            chat["private"] = True
    running = _gen.get(chat["id"], {})
    if running.get("done") is False:
        if not (chat.get("consortium") and running.get("consortium")):
            raise ValueError("дождись ответа на прошлое сообщение")
        CO.wait_stopped(running)  # the owner steps into the discussion
        from .. import achievements as ACH

        ACH.event(vault, "cons_interrupt")
    model = "consortium" if chat.get("consortium") else (model or chat.get("model") or default_model(vault))
    from .. import tuning

    if not chat.get("consortium"):
        split_model(model)
        tuning.check_month(vault, model.partition(":")[0])
    else:
        for ref in chat["consortium"]["members"]:
            tuning.check_month(vault, ref.partition(":")[0])
    prev_ai = next((m["text"] for m in reversed(chat["messages"]) if m["role"] == "assistant"), "")
    saved = save_files(vault, chat["id"], files) if files else []
    quote = (quote or "").strip()[:3000]
    if web is None:
        web = bool(P.load(vault).get("web"))
    if terms is None:
        terms = bool(P.load(vault).get("terms", True))
    msg = {
        "role": "user",
        "text": text,
        "ts": _now(),
        **({"quote": quote} if quote else {}),
        **({"web": True} if web else {}),
        **({"files": [dict(f) for f in saved]} if saved else {}),
        **({"hidden": True} if opener else {}),
    }

    def add(c):
        c["messages"].append(msg)
        c.update(model=model, updated=_now())

    if cid:
        chat = modify_chat(vault, chat["id"], add)
    else:
        add(chat)
        save_chat(vault, chat)

    from .. import achievements as ACH

    if not opener:
        ACH.event(vault, "message", text=text, quote=bool(quote), private=bool(chat.get("private")))
    for f in saved:
        ACH.event(vault, "file", ext=Path(f["name"]).suffix, chars=f.get("chars", 0))
    # learn from it right away — in parallel with the answer (unless this chat is private)
    if learn and not chat.get("private"):
        ep = Episode(
            "mnema_chat",
            f"{chat['id']}#{len(chat['messages'])}",
            _now(),
            text,
            prev=(quote or prev_ai)[-1500:],
            title=chat["title"],
        )
        threading.Thread(target=lambda: _safe_learn(vault, ep), daemon=True, name="mnema-learn-chat").start()
    if not opener and not chat.get("consortium") and not files and not quote:
        # A plain computer command («открой терминал», «запусти firefox», «open https://…») is one action and one line
        # of answer: no model round-trip, no 40–90 s wait, the same on every model.
        from . import intents as IN

        call = IN.fast_action(vault, text)
        if call is not None and not P.load(vault).get("tools_ask", False):
            say = IN.answer(vault, call)

            def add_brief(c):
                c["messages"].append({"role": "assistant", "text": say, "ts": _now(), "model": model})
                c["updated"] = _now()

            try:
                modify_chat(vault, chat["id"], add_brief)
            except KeyError:
                pass
            from .. import achievements as ACH

            ACH.event(vault, "action", tool="open_app")
            _gen[chat["id"]] = {"text": say, "done": True, "error": "", "phase": "", "stop": False}
            return {"chat": chat["id"], "title": chat["title"], "model": model}
    if chat.get("consortium"):
        return CO.start(vault, chat, text, sync, web, terms)
    from . import prompts as PRM

    d = {} if opener else PRM.decide(vault, chat, text)
    result = _generate(vault, chat, model, text, sync, web=web, terms=terms, prompt=d.get("use"))
    if "offer" in d:  # a recurring task: answer first, the recipe card only after it — never instead of the answer
        result["offer"] = True
        _offer_after(vault, result["chat"], text, d["offer"], model, web, terms, sync)
    return result


def _offer_msg(text: str, before: str, model: str, web: bool, terms: bool) -> dict:
    said = (
        f"Похожая задача уже была: «{before[:140].strip()}{'…' if len(before) > 140 else ''}». "
        if before
        else "Похоже, эта задача будет повторяться. "
    )
    return {
        "role": "assistant",
        "kind": "prompt_offer",
        "ts": _now(),
        "model": model,
        "text": said + "Записать рецепт этой задачи? В следующий раз сделаю так же — без объяснений и уточнений.",
        "offer": {"request": text, "similar": before, "web": web, "terms": terms},
    }


def _offer_after(
    vault: Vault, cid: str, text: str, before: str, model: str, web: bool, terms: bool, sync: bool
) -> None:
    """Put the «write a recipe?» card after the answer, so it can be read, used, or ignored."""

    def put() -> None:
        if not sync:  # wait for the answer itself (it streams in the background)
            for _ in range(1200):
                g = _gen.get(cid)
                if not g or g.get("done"):
                    break
                time.sleep(0.5)
        try:
            chat = load_chat(vault, cid)
        except KeyError:
            return
        msgs = chat.get("messages") or []
        if any(m.get("kind") == "prompt_offer" and not (m.get("offer") or {}).get("choice") for m in msgs[-4:]):
            return  # one unanswered offer is enough
        msg = _offer_msg(text, before, model, web, terms)
        modify_chat(vault, cid, lambda c: (c["messages"].append(msg), c.update(updated=_now())))

    if sync:
        put()
    else:
        threading.Thread(target=put, daemon=True, name="mnema-offer").start()


def _offer(vault: Vault, chat: dict, text: str, before: str, model: str, web: bool, terms: bool) -> dict:
    """The old blocking card (kept for callers that need the question before doing the task)."""
    msg = _offer_msg(text, before, model, web, terms)
    modify_chat(vault, chat["id"], lambda c: (c["messages"].append(msg), c.update(updated=_now())))
    _gen[chat["id"]] = {"text": "", "done": True, "error": "", "phase": "", "stop": False}
    return {"chat": chat["id"], "title": chat["title"], "model": model, "offer": True}


def answer_offer(vault: Vault, cid: str, choice: str, sync: bool = False) -> dict:
    """The owner's answer to «write a prompt?»: write | skip | never."""
    from . import prompts as PRM

    chat = load_chat(vault, cid)
    idx = next(
        (
            i
            for i in range(len(chat["messages"]) - 1, -1, -1)
            if chat["messages"][i].get("kind") == "prompt_offer" and not chat["messages"][i]["offer"].get("choice")
        ),
        None,
    )
    if idx is None:
        raise ValueError("нечего отвечать")
    offer = chat["messages"][idx]["offer"]
    model = chat.get("model") or default_model(vault)
    pid, mname = split_model(model)
    # in the new layout the card comes after the answer: the task is already done, so the answer must not be repeated
    answered_before = any(
        m.get("role") == "assistant" and m.get("kind") not in ("prompt_offer", "self_ask") and m.get("text")
        for m in chat["messages"][:idx]
    )

    def mark(extra: dict):
        def f(c):
            c["messages"][idx]["offer"].update(choice=choice, **extra)

        return modify_chat(vault, cid, f)

    if choice == "never":
        PRM.never(vault, offer["request"])
    if choice != "write":
        chat = mark({})
        if answered_before:  # «Просто сделать»: it has been done already
            return {"chat": cid}
        return _generate(
            vault, chat, model, offer["request"], sync, web=offer.get("web", False), terms=offer.get("terms", False)
        )
    g = {"text": "", "done": False, "error": "", "phase": "записываю рецепт задачи", "stop": False, "pid": pid}
    _gen[cid] = g

    def work():
        try:
            examples = "\n".join(f"- {x}" for x in [offer.get("similar"), offer["request"]] if x)
            system = system_prompt(vault, pid, log=False, query=offer["request"])
            written = PR.complete(
                vault, pid, mname, system, [{"role": "user", "text": PRM.WRITER.format(examples=examples)}]
            )
            name, when, body = PRM.parse_written(strip_thinking(written), short_title(offer["request"]))
            p = PRM.save(vault, name, when, body, offer["request"])
            if offer.get("similar"):
                p["examples"].insert(0, offer["similar"])
                PRM._write(vault, p)
            c = mark({"file": p["file"], "name": p["name"]})
            if answered_before:  # the answer is already there: saving the recipe is enough
                g["done"] = True
                return
            g["done"] = True
            _generate(
                vault,
                c,
                model,
                offer["request"],
                True,
                web=offer.get("web", False),
                terms=offer.get("terms", False),
                prompt=p,
            )
        except Exception as e:
            g["error"] = "не получилось записать рецепт: " + str(e)[:300]
            g["done"] = True

    if sync:
        work()
    else:
        threading.Thread(target=work, daemon=True, name="mnema-prompt").start()
    return {"chat": cid}


def regenerate(vault: Vault, cid: str, model: str = "", sync: bool = False) -> dict:
    """«Ещё раз»: drop the last answer and write it anew (no new learning — the words are the same)."""
    chat = load_chat(vault, cid)
    if _gen.get(cid, {}).get("done") is False:
        raise ValueError("дождись ответа")
    model = model or chat.get("model") or default_model(vault)

    def drop(c):
        while c["messages"] and c["messages"][-1]["role"] == "assistant":
            c["messages"].pop()
        if not c["messages"]:
            raise ValueError("нечего повторять")
        c.update(model=model, updated=_now())

    chat = modify_chat(vault, cid, drop)
    return _generate(vault, chat, model, chat["messages"][-1]["text"], sync, web=bool(chat["messages"][-1].get("web")))


WEB_NOTE = (
    "[Выдержки из авторитетных источников по вопросу владельца. Опирайся на них и ставь номер источника [1], [2] "
    "там, где берёшь из него факт. Не рассказывай, как и где искал, и не упоминай эти выдержки — просто ответь. "
    "Если в выдержках нет ответа, отвечай из своих знаний и прямо скажи, что не уверен]"
)


def _generate(
    vault: Vault,
    chat: dict,
    model: str,
    text: str,
    sync: bool,
    web: bool = False,
    terms: bool = False,
    prompt: dict | None = None,
) -> dict:
    from . import terms as TM

    pid, mname = split_model(model)
    g = {
        "text": "",
        "done": False,
        "error": "",
        "phase": "думаю",
        "started": time.time(),
        "stop": False,
        "pid": pid,
        "who": {
            "harness": "DeepSeek",
            "claude_code": "Claude",
            "anthropic": "Claude",
            "openai": "ChatGPT",
            "gemini": "Gemini",
        }.get(pid, ""),
    }
    _gen[chat["id"]] = g

    def work():
        nonlocal pid, mname  # no internet: the built-in model may take over
        try:
            from . import economy as EC

            from .. import tuning as TU

            eng = TU.get(vault)
            eco = eng["economy"]
            st: dict = {}
            system = system_prompt(
                vault, pid, log=len(chat["messages"]) == 1, query=text, stats=st, model=mname
            )  # journal: once per chat
            if terms:
                system += "\n\n" + TM.RULE
            from . import tools as TL

            acts = TL.enabled(vault) and text != OPENER
            if acts:  # the model may ask for an action; the owner says yes to each one
                from . import small as SM

                system += "\n\n" + TL.rule(vault, small=SM.is_small(pid, mname))
            if pid == "harness":  # its own DSH tools are off: every action goes through Mnemai's tools
                system += (
                    "\n\nСвоих инструментов у тебя нет — только действия Mnemai блоками ```mnema, как в правилах "
                    "выше. Не отвечай «у меня нет инструментов»: у тебя есть действия Mnemai."
                )
            if not web and text != OPENER:  # no search this time: it says so itself when it needs one
                system += "\n\n" + WEB_OFF
            if prompt:  # the owner's prompt for this recurring task
                from . import prompts as PRM

                system += "\n\n" + PRM.block(prompt)
                g["phase"] = f"готовлю по рецепту «{prompt['name']}»"
            msgs, full_h, sent_h = EC.build_history(
                chat, text, economy=eco, doc_budget=eng["docs"], history_budget=eng["history"]
            )
            from . import small

            if small.is_small(pid, mname) and msgs and msgs[-1]["role"] == "user":  # facts next to the question
                msgs[-1] = {**msgs[-1], "text": msgs[-1]["text"] + small.augment(vault, text)}
            if not eco:  # nothing trimmed on purpose — only web reading counts
                full_h = sent_h
            read_web, sent_web = 0, 0
            web_hid: dict = {}
            if web or EC.URL_RE.search(text):
                found = EC.web_context(text, web, budget=3500 if pid == "local" else 7000)  # a CPU model reads slowly
                if found.get("searched"):  # the search engines got a query: it is in «Что ушло наружу» too
                    from .. import outgoing as OG

                    OG.log(
                        vault,
                        "web",
                        "",
                        len(found.get("query", "")),
                        found.get("redacted") or {},
                        {"purpose": "поиск в интернете", "chat": chat["id"], "web": True},
                    )
                    web_hid = dict(found.get("redacted") or {})
                g["sources"] = found["sources"]
                read_web, sent_web = found["read_chars"], len(found["context"])
                note = f"{WEB_NOTE}\n{found['context']}" if found["context"] else ""
                if msgs and note:
                    q = msgs[-1]["text"]  # small local models lose a question buried under pages
                    msgs[-1] = {
                        **msgs[-1],
                        "text": (
                            f"Вопрос владельца: {q}\n\n{note}\n\nОтветь на вопрос владельца: {q}"
                            if pid == "local"
                            else note + "\n\n[Сообщение владельца]\n" + q
                        ),
                    }
            full = st.get("memory_full", 0) + full_h + read_web
            sent = st.get("memory_sent", 0) + sent_h + sent_web
            g["saved"] = EC.savings(full, sent)
            if pid == "local" and msgs and HOWTO_RE.search(msgs[-1]["text"]):
                # small local models drift from a long system prompt: the reference goes right next to the question
                from .selfknow import CONNECT

                msgs[-1] = {
                    **msgs[-1],
                    "text": msgs[-1]["text"] + "\n\n[Справка Mnemai. Отвечай только по ней, "
                    "адреса и названия кнопок не придумывай]\n" + CONNECT,
                }
            if pid == "local":
                from .. import localllm

                if not localllm.server_running(mname):
                    g["phase"] = "запускаю модель на компьютере"  # loading a model from disk takes 10–30 s
                localllm.ensure_server(mname, vault)
            g["phase"] = "пишу"
            g["started"] = time.time()
            usage: dict = {}
            g["usage"] = usage
            g["web_hid"] = web_hid
            from ..clients import get_client

            cl = get_client(vault, PR.PROVIDERS[pid]["client"])
            meta = {
                "purpose": "ответ в чате",
                "chat": chat["id"],
                "memory_sent": st.get("memory_sent", 0),
                "memory_full": st.get("memory_full", 0),
                "hidden_tags": list(cl.deny_tags),
                "web": bool(g.get("sources")),
                "hidden_parts": [
                    s
                    for s in ("profile", "rules", "projects", "cards", "people", "decisions", "inbox")
                    if not cl.allows(s)
                ],
            }
            steps = 0
            while True:
                try:
                    for piece in PR.stream(
                        vault, pid, mname, system, msgs, stop=lambda: g["stop"], usage=usage, meta=meta
                    ):
                        g["text"] += piece
                except Exception as e:
                    # no internet: the built-in model answers instead, if one is on this computer
                    from .. import errors as E, localllm

                    local = localllm.installed_models() if localllm.engine_ok() else []
                    if (
                        g["text"].strip()
                        or steps
                        or pid in ("local", "ollama", "strata")
                        or not local
                        or not E.no_network(e)
                    ):
                        raise
                    pid, mname = "local", local[0]["id"]
                    g["phase"] = "нет сети — отвечаю моделью на компьютере"
                    localllm.ensure_server(mname, vault)
                    system = system_prompt(vault, "local", log=False, query=text, model=mname)
                    g["text"] = f"_Нет сети — отвечает модель на компьютере ({local[0]['name']})._\n\n"
                    for piece in PR.stream(
                        vault, pid, mname, system, msgs, stop=lambda: g["stop"], usage=usage, meta=meta
                    ):
                        g["text"] += piece
                call = TL.parse(strip_thinking(g["text"])) if acts and not g["stop"] else None
                if not call:
                    break
                if steps >= TL.MAX_STEPS:
                    g["text"] = TL.before(strip_thinking(g["text"]), call) + (
                        "\n\n(Остановилась: слишком много действий подряд. Скажи, продолжать ли.)"
                    )
                    break
                steps += 1
                said = TL.before(strip_tool_markup(strip_thinking(g["text"])), call)
                if said:  # what it said before the action stays above the action's line
                    _add_msg(vault, chat["id"], {"role": "assistant", "text": said, "ts": _now(), "model": model})
                g["text"] = ""
                result = _act(vault, chat["id"], g, call, PR.PROVIDERS[pid]["client"], model)
                if result is None:  # stopped while waiting for the owner's word
                    break
                msgs = msgs + [
                    {
                        "role": "assistant",
                        "text": said + f"\n[action: {call['tool']} {call.get('path') or call.get('query') or ''}]",
                    },
                    {"role": "user", "text": "[Результат действия от Mnemai]\n" + result},
                ]
                g["text"] = ""
                g["phase"] = "пишу"
                g["started"] = time.time()
            g["text"] = strip_tool_markup(strip_thinking(g["text"]))
            if not web and not g.get("sources") and text != OPENER:  # Mnemai speaking first never needs the web
                from .. import web as W

                if WEB_MARK in g["text"] or W.needs_web(text):
                    g["needs_web"] = True
            g["text"] = g["text"].replace(WEB_MARK, "").rstrip()
            g["text"], g["terms"] = TM.split(g["text"])  # the glossary goes next to the answer, not into it
            if prompt and g["text"].strip():
                from . import prompts as PRM

                PRM.used(vault, prompt, text)
            if pid == "local":
                g["text"] = strip_unknown_links(g["text"], system + "\n".join(m["text"] for m in msgs))
                g["text"] = re.split(r"\n\s*\[?(?:Владелец|Пользователь|User)\b[^\n]*[:—]", g["text"])[0].rstrip()
            eff = P.effective(P.load(vault))
            if eff.get("second_pass") and g["text"].strip() and not g["stop"]:
                g["phase"] = "проверяю ответ"
                prof = P.load(vault)
                memory, _ = (
                    context_for(vault, PR.PROVIDERS[pid]["client"], log=False) if P.memory_on(vault) else ("", 0)
                )
                u2: dict = {}
                fixed = PR.complete(
                    vault,
                    pid,
                    mname,
                    SECOND_PASS.format(rules=P.rules_text(prof), memory=memory[:8000]),
                    [{"role": "user", "text": f"Сообщение владельца:\n{text}\n\nЧерновик ответа:\n{g['text']}"}],
                    usage=u2,
                    meta={"purpose": "проверка ответа", "chat": chat["id"]},
                )
                for k, v in u2.items():
                    if isinstance(v, (int, float)):
                        usage[k] = usage.get(k, 0) + v
                if fixed.strip():
                    g["checked"] = fixed.strip() != g["text"].strip()
                    g["text"] = fixed.strip()
            if not g["text"].strip() and not g["stop"]:  # the service answered with nothing at all
                from .. import errors as E

                g["error"] = (
                    f"{E.provider_name(pid)} ничего не ответил. Нажми «Ещё раз» или выбери другую модель слева вверху."
                )
        except Exception as e:
            from .. import errors as E

            g["error"] = E.human(e, E.provider_name(pid), mname, E.vpn_name(vault))
            if g["text"].strip():  # a part came before the failure: kept, marked as cut
                g["text"] = strip_tool_markup(strip_thinking(g["text"]))
                g["cut"] = bool(g["text"].strip())
        finally:
            if g.get("abandoned"):  # «Остановить» before the first word: the owner has moved on
                return

            def fin(c):
                if not g["text"].strip() and g["error"]:  # the error stays in the conversation
                    c["messages"].append(
                        {"role": "assistant", "text": "", "error": g["error"], "ts": _now(), "model": model}
                    )
                if g["text"].strip():
                    c["messages"].append(
                        {
                            "role": "assistant",
                            "text": g["text"],
                            "ts": _now(),
                            "model": model,
                            "checked": g.get("checked", False),
                            "tokens": {
                                k: v
                                for k, v in (g.get("usage") or {}).items()
                                if k not in ("progress", "reasoning", "redacted")
                            },
                            **({"redacted": hid} if (hid := _hidden(g)) else {}),
                            **({"sources": g["sources"]} if g.get("sources") else {}),
                            **({"saved": g["saved"]} if g.get("saved") else {}),
                            **({"terms": g["terms"]} if g.get("terms") else {}),
                            **({"prompt": prompt["name"]} if prompt else {}),
                            **({"needs_web": True} if g.get("needs_web") else {}),
                            **({"cut": True, "error": g["error"]} if g.get("cut") else {}),
                        }
                    )
                c["updated"] = _now()

            try:
                fresh = modify_chat(vault, chat["id"], fin)
                chat.update(fresh)
            except KeyError:  # deleted while answering
                pass
            if g["text"].strip():
                from .. import achievements as ACH

                ACH.event(
                    vault,
                    "answer",
                    pid=pid,
                    saved=g.get("saved", 0),
                    sources=len(g.get("sources") or []),
                    terms=len(g.get("terms") or []),
                    prompt=bool(prompt),
                )
            if g["text"].strip() and not g.get("cut") and not chat.get("private"):
                _maybe_self_ask(vault, chat["id"], text, model)
            g["phase"] = ""
            g["done"] = True
            if not chat.get("title_manual") and not chat.get("title_auto") and g["text"].strip():
                threading.Thread(target=_auto_title, args=(vault, chat["id"], pid, mname), daemon=True).start()

    if sync:
        work()
    else:
        threading.Thread(target=work, daemon=True, name="mnema-chat").start()
    return {"chat": chat["id"], "title": chat["title"], "model": model}


def _maybe_self_ask(vault: Vault, cid: str, text: str, model: str) -> None:
    """A question of Mnemai's own under the answer, when the talk is about a project (chat/selfask.py)."""
    from . import selfask as SA

    try:
        q = SA.pick(vault, text)
        if q:
            msg = {"role": "assistant", "kind": "self_ask", "ts": _now(), "model": model, "text": q["text"], "ask": q}
            modify_chat(vault, cid, lambda c: c["messages"].append(msg))
    except Exception:
        pass  # a question of her own is never worth a broken answer


def answer_self_ask(vault: Vault, cid: str, i: int, action: str, text: str = "") -> dict:
    """The owner's answer on the card: still | changed | gone | goal | skip | never."""
    from . import selfask as SA

    chat = load_chat(vault, cid)
    msgs = chat["messages"]
    if not (0 <= i < len(msgs)) or msgs[i].get("kind") != "self_ask" or msgs[i]["ask"].get("done"):
        raise ValueError("на этот вопрос уже ответили")
    line = SA.answer(vault, msgs[i]["ask"], action, text)

    def mark(c):
        c["messages"][i]["ask"].update(done=line, action=action)

    return modify_chat(vault, cid, mark)


HARNESS_NOTE = """=== Инструменты DeepSeek Harness ===
Ты отвечаешь как модель в Mnemai, но работаешь через агент DeepSeek Harness: у тебя ЕСТЬ его инструменты — bash
(терминал), чтение и запись файлов, поиск. Не пиши блоки ```mnema: просто выполни нужное инструментом и продолжи.
Владелец дал доступ к компьютеру по умолчанию. Не выводи в ответ пароли, ключи и токены.

Коротко — главное правило: одна-две фразы, сразу результат. Не пиши «Что сделал», «Детали», «Варианты», списки,
отчёты о проверках и команды — если владелец не попросил подробно. Не предлагай альтернативы, когда задача уже
выполнена. Если просят открыть программу — открой именно её, без рассказов о том, как искал."""

WEB_MARK = "{{нужен интернет}}"
WEB_OFF = (
    "Поиск в интернете сейчас выключен. Если для точного ответа нужны свежие данные из сети (цены, курсы, новости, "
    "события, расписания, версии программ), ответь, что знаешь сам, честно скажи, что данные могли измениться, и в самом "
    "конце отдельной строкой поставь метку " + WEB_MARK + " — Mnemai покажет владельцу кнопку включить поиск. "
    "Если ответ не зависит от свежих данных — метку не ставь."
)


def redo(vault: Vault, cid: str, web: bool = True) -> dict:
    """«Включить интернет и ответить заново»: the last answer is replaced by a new one, with the search on."""
    chat = load_chat(vault, cid)
    if _gen.get(cid, {}).get("done") is False:
        raise ValueError("дождись ответа")
    users = [m for m in chat["messages"] if m["role"] == "user"]
    if not users:
        raise ValueError("нечего переспрашивать")

    def drop(c):
        while c["messages"] and c["messages"][-1].get("kind") == "self_ask":  # a question card goes with its answer
            c["messages"].pop()
        if c["messages"] and c["messages"][-1]["role"] == "assistant":
            c["messages"].pop()

    chat = modify_chat(vault, cid, drop)
    model = chat.get("model") or default_model(vault)
    if chat.get("consortium"):
        raise ValueError("в консорциуме переспроси новым сообщением")
    return _generate(
        vault, chat, model, users[-1]["text"], False, web=web, terms=bool(P.load(vault).get("terms", True))
    )


def _safe_learn(vault: Vault, ep: Episode) -> None:
    try:
        learn.learn_episodes(vault, [ep], "mnema_chat")
    except Exception as e:  # learning must never break the chat
        learn.emit(vault, "ошибка", f"обучение: {e}", source="mnema_chat")


def learn_chat_now(vault: Vault, cid: str, limit: int = 30, brain=None) -> dict:
    """«Обновить память» on an expensive conversation: the whole conversation is learned right now, as one batch,
    so what was said across several messages is caught before a new session starts. A message already learned
    on its own does not count twice (same ref)."""
    chat = load_chat(vault, cid)
    if chat.get("private"):
        return {"skipped": "private"}
    eps, prev = [], ""
    for k, m in enumerate(chat.get("messages", [])):
        if m.get("role") == "assistant":
            prev = m.get("text", "")
            continue
        t = (m.get("text") or "").strip()
        if m.get("role") != "user" or not t or m.get("hidden"):
            continue
        eps.append(
            Episode(
                "mnema_chat",
                f"{cid}#{k + 1}",
                m.get("ts") or _now(),
                t[:4000],
                prev=(m.get("quote") or prev)[-1500:],
                title=chat.get("title", ""),
            )
        )
    if not eps:
        return {"skipped": "empty"}
    from ..learn import settings as LS

    st = LS.load(vault)
    if st.get("demo") or st["paused"] or not LS.allowed(st, "mnema_chat"):
        return {"skipped": "off"}
    rep = learn.learn_episodes(vault, eps[-limit:], "mnema_chat", brain=brain)
    out = {k: rep.get(k, 0) for k in ("new", "reinforced", "written")}
    if rep.get("errors"):
        out["error"] = rep["errors"][0]
    return out


def mark_useful(vault: Vault, cid: str, index: int, on: bool = True) -> dict:
    """«Полезно» under an answer: kept as an example of the shape he likes, and a learning signal."""

    def mark(chat):
        msgs = chat["messages"]
        if not (0 <= index < len(msgs)) or msgs[index]["role"] != "assistant":
            raise ValueError("это не ответ")
        msgs[index]["useful"] = bool(on)

    chat = modify_chat(vault, cid, mark)
    msgs = chat["messages"]
    if on and not chat.get("private"):
        question = next((m["text"] for m in reversed(msgs[:index]) if m["role"] == "user"), "")
        threading.Thread(target=_learn_useful, args=(vault, question, msgs[index]["text"]), daemon=True).start()
    return {"ok": True, "useful": bool(on)}


USEFUL = """{mark}
Владелец отметил ответ ассистента как «Полезно». Сформулируй одной короткой строкой, что в ФОРМЕ и ПОДХОДЕ ответа
ему подошло (структура, длина, тон, конкретика), а не содержание. Начни с глагола, как правило для ассистента.
Пример: «Давай план по дням с датами, без вступления». Верни только строку.

Вопрос владельца: {q}

Ответ: {a}"""


def _learn_useful(vault: Vault, question: str, answer: str) -> None:
    from ..learn import settings as S
    from ..learn.brains import make_brain
    from ..learn.ledger import Ledger
    from ..learn.sources import BRAIN_MARK

    s = S.load(vault)
    learn.emit(
        vault,
        "заметила",
        "тебе подошёл этот ответ",
        why="отметка «Полезно»: похожие ответы буду строить так же",
        source="mnema_chat",
        quote=answer[:160],
    )
    if s.get("demo") or S.resolve_brain(s) == "none":
        return
    try:
        brain = make_brain(s)
        brain.vault = vault
        ask = getattr(brain, "_ask_safe", None) or brain.ask
        rule = (
            ask(USEFUL.format(mark=BRAIN_MARK, q=question[:1500], a=answer[:3000])).strip().strip('"«»').splitlines()[0]
        )
    except Exception as e:
        learn.emit(vault, "ошибка", f"не поняла, что подошло: {e}", source="mnema_chat")
        return
    if not (6 <= len(rule) <= 200):
        return
    led = Ledger(vault)
    c = {
        "text": rule,
        "kind": "rule",
        "where": "rules",
        "key": "форма ответа",
        "tags": [],
        "confidence": 0.55,
        "evidence": "отметка «Полезно»",
        "ref": "useful",
        "source": "mnema_chat",
        "contradicts": "",
        "correction": False,
    }
    learn.consider(vault, led, c, s, learn.new_report(), learn.memory_lines(vault))
    led.save()


TITLE = """Придумай название этого разговора: от одного до трёх слов, на языке: {lang}, по сути, без кавычек, точки и слова «разговор».
Верни только название.

Владелец: {q}

Ответ: {a}"""


def short_title(text: str) -> str:
    """Fallback without a model: the first three meaningful words."""
    stop = {
        "и",
        "а",
        "но",
        "что",
        "как",
        "я",
        "ты",
        "мне",
        "мой",
        "моя",
        "это",
        "в",
        "на",
        "по",
        "с",
        "о",
        "об",
        "у",
        "к",
        "для",
        "мы",
        "вы",
        "он",
        "она",
        "привет",
        "пожалуйста",
        "можешь",
        "скажи",
        "помоги",
        "давай",
    }
    words = [w for w in re.findall(r"[\wё-]+", text.lower()) if w not in stop and len(w) > 1]
    t = " ".join(words[:3]) or "Разговор"
    return t[:1].upper() + t[1:]


def _auto_title(vault: Vault, cid: str, pid: str, model: str) -> None:
    """After the first answer: a 1–3 word name, made by the same provider (the fast model for Claude)."""
    try:
        chat = load_chat(vault, cid)
        if chat.get("title_manual") or chat.get("title_auto"):
            return
        q = next((m["text"] for m in chat["messages"] if m["role"] == "user" and not m.get("hidden")), "")
        a = next((m["text"] for m in chat["messages"] if m["role"] == "assistant"), "")
        usage: dict = {}
        title = ""
        try:
            if pid == "local":  # the CPU model is slow and would lose what it has read
                raise RuntimeError("без модели")
            title = PR.complete(
                vault,
                pid,
                "haiku" if pid == "claude_code" else model,
                "Ты придумываешь короткие названия.",
                [
                    {
                        "role": "user",
                        "text": TITLE.format(
                            q=q[:1500], a=a[:1500], lang=LANG_NAMES.get(P.load(vault).get("lang") or "en", "русский")
                        ),
                    }
                ],
                usage=usage,
                meta={"purpose": "название разговора", "chat": cid},
            )
        except Exception:
            pass
        title = " ".join(
            re.sub(r"[\"«».:]+", " ", (title or "").strip().splitlines()[0] if title.strip() else "").split()
        )
        if not title or len(title.split()) > 3 or len(title) > 40:
            title = short_title(q)

        def put(c):
            if not c.get("title_manual"):  # the owner may have renamed it meanwhile
                c.update(title=title[:1].upper() + title[1:], title_auto=True, title_tokens=usage)

        modify_chat(vault, cid, put)
    except Exception:
        pass


URL_RE = re.compile(r"<?(https?://[^\s<>)\]]+|\b[\w-]+(?:\.[\w-]+)+/[^\s<>)\]]*)>?")


def strip_unknown_links(text: str, known: str) -> str:
    """Small local models invent addresses. Keep only links that Mnemai itself gave them; drop the rest."""

    def keep(m):
        url = m.group(1).rstrip(".,;:")
        bare = re.sub(r"^https?://(www\.)?", "", url).rstrip("/")
        return m.group(0) if bare and bare.split("/")[0] in known else ""

    out = URL_RE.sub(keep, text)
    return re.sub(r"[ \t]+\n", "\n", re.sub(r"(по ссылке|по адресу)\s*:?\s*(?=[.\n]|$)", "", out))
