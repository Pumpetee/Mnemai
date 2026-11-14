"""Token economy: do on the computer whatever can be done there, send the model only what the question needs.

- memory: the head (who the owner is, rules, "now") always goes; the rest — only lines relevant to the question;
- documents: read locally once; each turn only the passages that match the current question go to the model;
  older turns mention the file instead of repeating it;
- history: the last turns in full, older ones shortened;
- web: search and page reading happen locally, the model gets numbered excerpts with links.
Every answer records an estimate of the tokens saved this way.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..retrieve import best, est_tokens, rank
from .attach import inline_text

KEEP_LAST = 6
OLD_MSG_CHARS = 400
HISTORY_BUDGET = 14000
DOC_BUDGET = 7000


def compact_memory(memory: str, query: str, head: int = 2200, budget: int = 4200) -> str:
    """Memory head + the lines relevant to the question."""
    if len(memory) <= budget:
        return memory
    rest = memory[head:]
    lines = [l for l in rest.splitlines() if l.strip()]
    heads = [l for l in lines if l.startswith("===")]
    body = [l for l in lines if not l.startswith("===")]
    picked, size = [], 0
    for score, i in rank(query, body):
        if score <= 0 or size + len(body[i]) > budget - head:
            break
        picked.append(i)
        size += len(body[i]) + 1
    kept = "\n".join(body[i] for i in sorted(picked))
    return (
        memory[:head]
        + "\n…\n"
        + ("Разделы памяти: " + ", ".join(h.strip("= ") for h in heads) + "\n" if heads else "")
        + ("Относится к вопросу:\n" + kept if kept else "")
    )


def doc_text(f: dict) -> str:
    if f.get("text_path") and Path(f["text_path"]).exists():
        return Path(f["text_path"]).read_text(encoding="utf-8", errors="replace")
    return f.get("text", "")


def build_history(
    chat: dict, query: str, economy: bool = True, doc_budget: int = DOC_BUDGET, history_budget: int = HISTORY_BUDGET
) -> tuple[list[dict], int, int]:
    """(messages for the model, chars without economy, chars actually sent). The budgets come from «Точнее ↔
    Экономнее» in Настройки → Движок."""
    msgs = [m for m in chat["messages"] if m["role"] in ("user", "assistant") and m.get("text") and not m.get("kind")]
    docs = [(m, f) for m in msgs for f in (m.get("files") or []) if f.get("kind") == "text"]
    full = sum(len(m["text"]) for m in msgs) + sum(len(doc_text(f)) for _, f in docs)
    out, size = [], 0
    for idx in range(len(msgs) - 1, -1, -1):
        m = msgs[idx]
        newest = idx == len(msgs) - 1
        body = m["text"]
        if m.get("quote"):
            quoted = "\n".join("> " + l for l in m["quote"].splitlines())
            body = f"[Отвечаю на этот фрагмент твоего ответа]\n{quoted}\n\n{body}"
        files = m.get("files") or []
        if not economy:
            body = inline_text(body, files)
        else:
            if len(msgs) - idx > KEEP_LAST and len(body) > OLD_MSG_CHARS:
                body = body[:OLD_MSG_CHARS] + " …[сокращено]"
            names = [f["name"] for f in files if f.get("kind") == "text"]
            if names and not newest:
                body += "\n[Прикреплено: " + ", ".join(names) + " — нужные места подставляются к последнему вопросу]"
            body = inline_text(body, [f for f in files if f.get("kind") == "other"])
        size += len(body)
        if economy and size > history_budget and out:
            break
        out.append({"role": m["role"], "text": body, "files": files if newest else None})
    out.reverse()
    if economy and docs and out:
        # all documents of this chat, searched locally for the current question
        per = max(1500, doc_budget // len(docs))
        parts = []
        for _, f in docs[-6:]:
            excerpt, cut = best(query, doc_text(f), budget=per)
            parts.append(f"[Документ «{f['name']}»{' — найденные по вопросу места' if cut else ''}]\n{excerpt}")
        out[-1] = {**out[-1], "text": "\n\n".join(parts) + "\n\n[Сообщение владельца]\n" + out[-1]["text"]}
    sent = sum(len(m["text"]) for m in out)
    return out, full, sent


URL_RE = re.compile(r"https?://[^\s<>\"')\]]+")


def web_context(text: str, search: bool, budget: int = 7000) -> dict:
    """Pages from links in the message always; a web search when the owner switched «Интернет» on."""
    from .. import web

    urls = URL_RE.findall(text)[:3]
    if search and not urls and not web.should_search(text):
        search = False  # "Интернет" is allowed, but this message doesn't need it
    if not urls and not search:
        return {"context": "", "sources": [], "read_chars": 0, "searched": False}
    from ..outgoing import LABEL_RE, Redactor

    red = Redactor()
    q = LABEL_RE.sub(" ", red.apply(URL_RE.sub(" ", text))).strip() or "?"  # a search engine never gets a secret
    found = web.gather(q, urls=urls or None, pages=3 if urls else 4, budget=budget, search_too=bool(urls and search))
    # Some pages contain control bytes or lone surrogates; providers reject such a request with a generic 400.
    context = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", found.get("context") or "")
    context = context.encode("utf-8", "replace").decode("utf-8")
    if len(context) > budget:
        context = context[:budget].rsplit("\n", 1)[0]
    found = {**found, "context": context}
    return {**found, "searched": bool(search), "query": q, "redacted": red.summary()}


def savings(full_chars: int, sent_chars: int) -> int:
    return max(0, est_tokens(full_chars - sent_chars))
