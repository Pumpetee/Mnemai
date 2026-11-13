"""Questions from Mnemai herself. When the conversation is about one of the owner's projects, now and then one short
question about it, shown as a card under the answer (like «Записать рецепт»): a status that is over a month old, or a
project without a goal. Not more often than once in 40–120 minutes — after each question the pause is drawn anew —
never in a conversation without learning, never with the memory off. The answer goes straight into the memory.
"""

from __future__ import annotations

import datetime as dt
import random
import re

from ..agent import profile as P
from ..retrieve import stem
from ..vault import Vault

GAP_MIN, GAP_MAX = 40, 120  # minutes between two questions

# A message that asks Mnemai to show or check the memory is not an invitation for a question of her own: the owner is
# already waiting for an answer, not for a new card.
RECALL = re.compile(
    r"(?:что\s+(?:ты\s+)?(?:записал|запомнил|помнишь|знаешь)|перечисли|покажи\s+.{0,20}(?:памят|факт|проект)|"
    r"список\s+(?:факт|запис|проект)|проверь\s+памят|что\s+(?:в|из)\s+памяти|что\s+записано)",
    re.I,
)


def _words(text: str) -> set[str]:
    return {stem(w) for w in re.findall(r"\w{3,}", text.lower())}


def _same(a: str, b: str) -> bool:
    """One word in two forms: «новый» and «новому», «склад» and «склада»."""
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n >= max(3, min(len(a), len(b)) - 2)


def _project(vault: Vault, text: str):
    """The open project the message is about: every word of its name is in it, in any form."""
    said = _words(text)
    best, size = None, 0
    for n in vault.by_scope("projects"):
        if str(n.meta.get("status", "active")) not in ("active", "paused"):
            continue
        name = _words(n.title)
        if name and all(any(_same(w, s) for s in said) for w in name) and len(name) > size:
            best, size = n, len(name)
    return best


def pick(vault: Vault, text: str, now: dt.datetime | None = None, today: dt.date | None = None) -> dict | None:
    """The question to ask after this answer, or None. Asking moves the next possible one 40–120 minutes ahead."""
    from ..memory import stale_items

    now = now or dt.datetime.now()
    if RECALL.search(text):
        return None  # the owner asked about the memory itself: answer first, ask nothing
    prof = P.load(vault)
    if not P.memory_on(vault) or prof.get("self_ask") is False:
        return None
    nxt = str(prof.get("self_ask_next") or "")
    if nxt and now.isoformat(timespec="seconds") < nxt:
        return None
    note = _project(vault, text)
    if not note:
        return None
    title = note.title
    stale = [s for s in stale_items(vault, today) if s["where"] == note.rel]
    if stale:
        s = stale[0]
        when = dt.date.fromisoformat(s["date"]).strftime("%d.%m.%Y")
        if s["text"].endswith(": проект не обновлялся"):
            q = {
                "type": "stale",
                "text": f"Проект «{title}» не обновлялся с {when}. Он ещё в работе?",
                "options": [["still", "Да, в работе"], ["changed", "Изменилось"], ["gone", "Закрыт"]],
            }
        else:
            q = {
                "type": "stale",
                "text": f"По проекту «{title}» у меня записано от {when}: «{s['text']}». Всё ещё так?",
                "options": [["still", "Да, так"], ["changed", "Изменилось"], ["gone", "Уже не актуально"]],
            }
        q["item"] = s["id"]
    elif not str(note.meta.get("goal") or "").strip():
        q = {
            "type": "goal",
            "text": f"Какая сейчас главная цель проекта «{title}»? Запишу и буду опираться на неё.",
            "options": [["goal", "Записать"]],
        }
    else:
        return None
    q["project"] = title
    later = now + dt.timedelta(minutes=random.uniform(GAP_MIN, GAP_MAX))
    P.save(vault, {"self_ask_next": later.isoformat(timespec="seconds")})
    return q


def answer(vault: Vault, q: dict, action: str, text: str = "") -> str:
    """Apply the owner's answer; returns the line the card shows afterwards."""
    from ..memory import remember, resolve_stale

    text = (text or "").strip()
    if action == "skip":
        return "Хорошо, не сейчас."
    if action == "never":
        P.save(vault, {"self_ask": False})
        return "Больше не спрашиваю сама. Включить — Настройки → Обучение."
    if q.get("type") == "goal":
        if not text:
            raise ValueError("Напиши цель одной фразой")
        remember(vault, f"Цель: {text}", f"project:{q['project']}", "owner")
        return f"Записала цель: {text}"
    if action == "changed" and not text:
        raise ValueError("Напиши, что изменилось")
    resolve_stale(vault, str(q.get("item", "")), action if action in ("still", "changed", "gone") else "still", text)
    return {"still": "Отметила: всё в силе.", "gone": "Убрала в архив."}.get(action, f"Записала: {text}")
