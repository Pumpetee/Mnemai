"""Consortium: a live discussion of 2–4 AIs for the owner.

The owner asks; the AIs speak in turn, round after round, each seeing what the others said — they agree, argue and
add, addressing each other by name. The last speaker of the last round sums up: where they agreed, where not, what
they advise.

The owner runs it like a round table:
- it can be switched on in a conversation that is already going — the AIs read it and help where there was no clarity;
- members and the number of rounds change at any moment, also while they talk (read before every turn);
- «Пауза» — the current speaker finishes, the others wait; «Продолжить» or any message of the owner goes on from
  the next speaker;
- «Завершить» — the current speaker is cut, one AI sums up right away;
- an AI asks the owner a question (an ask block) — the others wait; the answer goes on from the next speaker;
- a message of the owner while they talk — the current speaker is cut and the round goes on from the next one,
  everybody sees the message.
Where the discussion stands is kept in chat["consortium"]["state"]: status running / paused / waiting / done,
round and the index of the next speaker.

Every participant gets Mnemai's memory under its own access rules (system_prompt by provider), so a model that may
not see money doesn't see it here either.
"""

from __future__ import annotations

import re
import threading
import time

from . import providers as PR

MAX_MEMBERS = 4
MAX_ROUNDS = 20
OLD_CHARS = 1500  # an older message is cut to this many characters…
KEEP_FULL = 16  # …the last ones go whole


def _pretty(mid: str) -> str:
    """ "claude-sonnet-4-5" → "Claude Sonnet 4.5": words capitalised, version numbers joined with a dot."""
    out: list[str] = []
    for part in mid.split("-"):
        if part.isdigit() and len(part) <= 2 and out and out[-1].replace(".", "").isdigit():
            out[-1] += "." + part
        else:
            out.append(part if part.isdigit() else part[:1].upper() + part[1:])
    return " ".join(out)


def speaker_name(ref: str, vault=None) -> str:
    pid, _, mid = ref.partition(":")
    if pid == "claude_code":
        return {"": "Claude", "sonnet": "Claude Sonnet", "opus": "Claude Opus", "haiku": "Claude Haiku"}.get(
            mid, "Claude " + mid
        )
    if pid == "local":
        from .. import localllm

        m = localllm.BY_ID.get(mid)
        return m["name"] if m else (mid or "Локальная модель")
    if pid == "anthropic":
        return _pretty(mid) if mid else "Claude"
    base = {
        "openai": "ChatGPT",
        "gemini": "Gemini",
        "openrouter": "",
        "ollama": "",
        "deepseek": "",
        "yandex": "",
        "strata": "",
    }.get(pid, "")
    return f"{base} · {mid}" if base and mid else (mid or PR.PROVIDERS.get(pid, {}).get("name", pid))


def names_for(members: list[str]) -> dict[str, str]:
    """ref → unique display name."""
    out, used = {}, {}
    for ref in members:
        n = speaker_name(ref)
        used[n] = used.get(n, 0) + 1
        out[ref] = n if used[n] == 1 else f"{n} ({used[n]})"
    return out


def clean(cfg: dict | None) -> dict | None:
    if not cfg:
        return None
    members = []
    for ref in cfg.get("members") or []:
        ref = str(ref)
        if ref.partition(":")[0] in PR.PROVIDERS and ref not in members:
            members.append(ref)
    if len(members) < 2:
        raise ValueError("для консорциума нужны хотя бы два ИИ")
    out = {"members": members[:MAX_MEMBERS], "rounds": max(1, min(MAX_ROUNDS, int(cfg.get("rounds") or 2)))}
    out["format"] = cfg.get("format") if cfg.get("format") in FORMATS else "council"
    out["roles"] = {r: v for r, v in (cfg.get("roles") or {}).items() if r in out["members"] and v in ROLES and v}
    out["summarizer"] = cfg.get("summarizer") if cfg.get("summarizer") in out["members"] else ""
    out["length"] = cfg.get("length") if cfg.get("length") in LENGTHS else "normal"
    out["search"] = bool(cfg.get("search", True))  # the speakers may look things up to back their words
    for k in ("state", "from"):  # where the discussion stands, what chat it grew from
        if cfg.get(k):
            out[k] = cfg[k]
    ch = cfg.get("challenge")  # «Поспорить с разными ИИ»: one answer, defended by its author, questioned by the rest
    if isinstance(ch, dict) and ch.get("answer") and ch.get("by") in out["members"]:
        out["challenge"] = {
            "by": ch["by"],
            "answer": str(ch["answer"])[:4000],
            "question": str(ch.get("question") or "")[:2000],
        }
    return out


RULES = """=== Консорциум ===
Ты участвуешь в совете нескольких ИИ, который отвечает владельцу на его вопрос. Участники по порядку: {names}. Ты — {me}.

ВОПРОС ВЛАДЕЛЬЦА, на который отвечает весь совет:
«{question}»

{stage}

Как выступать:
- Пиши владельцу, а не другим ИИ. Первая фраза — по существу задачи этого круга и всегда про его вопрос.
- Опирайся на сказанное другими: соглашайся или спорь с доводами, называя участника по имени из списка. Не пересказывай их.
- Не уходи в сторону от вопроса. Не выдумывай факты и цифры: чего не знаешь — так и скажи.
- Не больше {words} слов. Без вступлений, без приветствий и без подписи.{role}
- Если без ответа владельца дальше не продвинуться — задай ему один вопрос блоком ask, остальные подождут.{search}{joined}{final}"""

SEARCH_RULE = """
- Можешь проверить себя в интернете. Если опираешься на факт, цифру, дату или свежие сведения, в которых не уверен,
  или споришь с чужим утверждением о фактах — напиши ТОЛЬКО строку [поиск: короткий запрос] (не больше двух таких строк)
  и больше ничего. Mnemai найдёт и пришлёт выдержки, тогда ответишь, ставя номера источников [1], [2].
  На мнения, советы и рассуждения не ищи."""

SEARCH_DONE = """

[Выдержки из интернета по твоим запросам ({queries}). Опирайся на них и ставь номер источника [1], [2] у факта, который
из него берёшь. Новых запросов не делай. Если выдержки не подтвердили твоё утверждение — скажи об этом прямо.]
{context}"""

SEARCH_RE = re.compile(r"^\s*\[поиск:\s*([^\]\n]{2,160})\]\s*$", re.M)
MAX_SEARCHES = 2


# What each round is for. «Свой ответ» comes first, «Общий ответ» last; with more than five rounds the middle three
# repeat. Every stage names the owner's question, so the speakers answer it instead of talking to each other.
STAGES = {
    "own": (
        "Свой ответ",
        "Круг «Свой ответ». Ответь на вопрос владельца сам — прямо, конкретно, так, чтобы этим можно было "
        "пользоваться. Первая фраза — ответ. Если до тебя уже ответили — не повторяй, дай свой вариант или свой довод.",
    ),
    "check": (
        "Проверка",
        "Круг «Проверка». Проверь ответы других: у каждого назови одно главное слабое место — что неверно, "
        "что упущено, где риск — и чем ты не согласен. Если тебя убедили — честно поправь свой ответ.",
    ),
    "better": (
        "Улучшение",
        "Круг «Улучшение». Собери из сказанного лучший ответ на вопрос владельца: возьми сильное у всех, "
        "убери слабое. Конкретика: шаги, варианты, условия, когда что выбирать.",
    ),
    "dispute": (
        "Спорное",
        "Круг «Спорное». Назови, что ещё не решено или в чём вы расходитесь, и как это решить: какой факт "
        "проверить, что спросить у владельца. Если спорного нет — коротко подтверди и добавь, что стоит учесть.",
    ),
    "final": (
        "Общий ответ",
        "Круг «Общий ответ». Сформулируй ответ на вопрос владельца, с которым согласен весь совет: "
        "сначала сам ответ одной-двумя фразами, потом 3–5 пунктов. Если кто-то не согласен — скажи, в чём.",
    ),
}


STAGES.update(
    {
        "pos": (
            "Позиции",
            "Круг «Позиции». Займи свою сторону (она указана ниже) и приведи 2–3 самых сильных довода с фактами. "
            "Первая фраза — твоя позиция одним предложением.",
        ),
        "rebut": (
            "Возражения",
            "Круг «Возражения». Ответь на самый сильный довод другой стороны: где он неверен, чего не учитывает. "
            "Признай, если он тебя частично убедил.",
        ),
        "verdict": (
            "Вердикт",
            "Круг «Вердикт». Взвесь доводы обеих сторон честно, без своей стороны: что весомее и при каких "
            "условиях решение меняется. Сначала вердикт одной фразой.",
        ),
        "ideas": (
            "Идеи",
            "Круг «Идеи». Дай 3–5 разных идей, как решить вопрос владельца, по одной строке каждая. Без критики "
            "чужих идей и без повторов.",
        ),
        "grow": (
            "Развитие",
            "Круг «Развитие». Возьми одну-две чужие идеи и сделай их сильнее: что добавить, как совместить, "
            "как проверить быстро и дёшево.",
        ),
        "best": (
            "Лучшие идеи",
            "Круг «Лучшие идеи». Выбери 3 лучшие идеи из всех и для каждой скажи: почему она, первый шаг, "
            "главный риск.",
        ),
        "attack": (
            "Атака",
            "Круг «Атака». Ищи дыры в плане или идее владельца: что сломается, где деньги и время уйдут впустую, "
            "какие допущения ложные. Самое опасное — первым.",
        ),
        "fix": (
            "Как закрыть",
            "Круг «Как закрыть». Для самых опасных дыр, найденных другими, предложи, как их закрыть или проверить "
            "до запуска.",
        ),
        "roast": (
            "Прожарка",
            "Круг «Прожарка». Разнеси то, что принёс владелец (идею, текст, резюме, план, страницу): три самых слабых "
            "места, жёстко и по делу, без шуток и без оскорблений самого человека. Каждое — одной-двумя фразами.",
        ),
        "roast2": (
            "Добивка",
            "Круг «Добивка». Добавь то, что другие пропустили, или заступись, если кто-то придрался зря. Без повторов.",
        ),
        "score": (
            "Оценка",
            "Круг «Оценка». Подведи итог прожарки: насколько всё плохо и что чинить первым.",
        ),
        "risks": (
            "Риски и что делать",
            "Круг «Риски и что делать». Сведи всё в список: риск, насколько опасен, что сделать. "
            "Сначала самый опасный.",
        ),
    }
)

# How the discussion goes: the first round, the rounds that repeat, the last round.
FORMATS = {
    "council": {"name": "Совет", "first": "own", "middle": ("check", "better", "dispute"), "last": "final"},
    "debate": {"name": "Дебаты", "first": "pos", "middle": ("rebut",), "last": "verdict"},
    "brainstorm": {"name": "Мозговой штурм", "first": "ideas", "middle": ("grow",), "last": "best"},
    "redteam": {"name": "Красная команда", "first": "attack", "middle": ("fix", "attack"), "last": "risks"},
    "roast": {"name": "Прожарка", "first": "roast", "middle": ("roast2",), "last": "score"},
}
ROLES = {
    "": "",
    "skeptic": "Скептик: ищешь, где ошибка и что не сработает",
    "practitioner": "Практик: как сделать руками — шаги, сроки, ресурсы",
    "finance": "Финансист: деньги — стоимость, окупаемость, риск потерь",
    "lawyer": "Юрист: законность, договоры, ответственность",
    "creative": "Креативщик: нестандартные ходы и неожиданные идеи",
    "analyst": "Аналитик: цифры, факты и что нужно проверить",
    "client": "Клиент: смотришь глазами покупателя или пользователя",
}
LENGTHS = {"short": (80, 120), "normal": (150, 180), "long": (300, 350)}


def order(cfg: dict, r: int) -> list:
    """Who speaks in round r: in the last round the chosen summarizer goes last."""
    members, s = list(cfg["members"]), cfg.get("summarizer") or ""
    if r == cfg["rounds"] - 1 and s in members:
        members = [m for m in members if m != s] + [s]
    return members


def side_of(cfg: dict, ref: str) -> str:
    """Debates: the first, third… speaker argues for, the others against."""
    if cfg.get("format") != "debate" or ref not in cfg["members"]:
        return ""
    ch = cfg.get("challenge")
    if ch:  # the author defends the answer, everyone else looks for where it is wrong
        if ref == ch["by"]:
            return "ЗА — отстаивай свой ответ там, где он верен, и честно признай, где он ошибся"
        return "ПРОТИВ — ищи, где этот ответ неверен, неполон или есть вариант лучше"
    if cfg["members"].index(ref) % 2 == 0:
        return "ЗА — отстаивай, что это верно и стоит делать"
    return "ПРОТИВ — отстаивай, что это неверно или делать не стоит"


def stage_of(r: int, rounds: int, fmt: str = "council") -> str:
    """Round index (from 0) → stage key."""
    if fmt in FORMATS and fmt != "council":
        f = FORMATS[fmt]
        if rounds == 1:
            return f["last"]
        if r == 0:
            return f["first"]
        if r == rounds - 1:
            return f["last"]
        return f["middle"][(r - 1) % len(f["middle"])]
    plans = {1: ["own"], 2: ["own", "final"], 3: ["own", "check", "final"], 4: ["own", "check", "better", "final"]}
    if rounds in plans:
        return plans[rounds][r]
    if r == 0:
        return "own"
    if r == rounds - 1:
        return "final"
    return ("check", "better", "dispute")[(r - 1) % 3]


CHALLENGE = (
    "\nВладелец попросил поспорить с ответом {model}. Вот этот ответ:\n«{answer}»\n"
    "Разберите его по существу: где он верен, где ошибается или неполон, и что было бы лучше. В конце — итог: "
    "держится ответ или нет и что владельцу делать."
)
JOINED = (
    "\nВладелец подключил вас к разговору, который уже шёл с {model}: ясности там не получилось. Разговор выше — "
    "контекст; отвечайте на последний вопрос владельца, учитывая, где прошлый ответ не помог."
)
ROAST_FINAL = (
    "\n\nТЫ ПОДВОДИШЬ ИТОГ ПРОЖАРКИ. Первая строка — только оценка в виде «N/10», где N — честное целое от 1 до 10, "
    "без других слов. Вторая — вердикт одной фразой. Потом ровно три пункта «- …»: что исправить первым, по одной "
    "строке. Не больше {fwords} слов."
)
ROAST_RE = re.compile(r"^\W*(\d{1,2})\s*/\s*10\b", re.M)
FINAL = (
    "\n\nТЫ ПОДВОДИШЬ ИТОГ. Начни со слова «Итог:» и сразу дай прямой ответ на вопрос владельца одной-двумя фразами. "
    "Потом коротко: в чём совет сошёлся, в чём разошёлся и что вы советуете сделать. Не больше {fwords} слов."
)


DOC_PER = 4000  # characters of one attached document each participant gets: the places that answer the question


def _owner_packed(m: dict, query: str, body: str) -> str:
    """The owner's message the way every participant gets it: the fragment he answers, the text of what he attached
    (documents — the places about the question, pictures — the text read off them), not just the words he typed."""
    from .attach import inline_text
    from .economy import doc_text
    from ..retrieve import best

    if m.get("quote"):
        body = "[Отвечает на фрагмент]\n" + "\n".join("> " + x for x in m["quote"].splitlines()) + "\n\n" + body
    files = m.get("files") or []
    body = inline_text(body, [f for f in files if f.get("kind") != "text"])
    for f in files:
        if f.get("kind") == "text":
            excerpt, cut = best(query or m["text"], doc_text(f), budget=DOC_PER)
            body += f"\n\n[Документ «{f['name']}»{' — места, относящиеся к вопросу' if cut else ''}]\n{excerpt}"
    return body


def history(chat: dict, me: str, names: dict[str, str], query: str = "") -> list[dict]:
    """The whole conversation packed for this participant — also what was said before the council met, with the
    attached files: its own words are its turns, the owner's and others' — the other side."""
    seq = []
    msgs = [m for m in chat["messages"] if m["role"] in ("user", "assistant") and m.get("text") and not m.get("kind")]
    for i, m in enumerate(msgs):
        text = m["text"]
        if len(msgs) - i > KEEP_FULL and len(text) > OLD_CHARS:
            text = text[:OLD_CHARS] + " …[сокращено]"
        if m["role"] == "user":
            seq.append(("user", f"Владелец: {_owner_packed(m, query, text)}"))
        elif m.get("model") == me:
            seq.append(("assistant", text))
        else:
            seq.append(
                (
                    "user",
                    f"{m.get('speaker') or names.get(m.get('model', '')) or speaker_name(m.get('model') or '') or 'Другой ИИ'}: {text}",
                )
            )
    out: list[dict] = []
    for role, text in seq:  # providers want alternating turns
        if out and out[-1]["role"] == role:
            out[-1]["text"] += "\n\n" + text
        else:
            out.append({"role": role, "text": text})
    if not out or out[0]["role"] != "user":
        out.insert(0, {"role": "user", "text": "Владелец открыл обсуждение."})
    if out[-1]["role"] != "user":
        out.append({"role": "user", "text": "Продолжай обсуждение."})
    # pictures and PDFs of the owner's latest message with files go to every participant as they are
    last = next((m for m in reversed(msgs) if m["role"] == "user" and m.get("files")), None)
    seen = [f for f in (last or {}).get("files") or [] if f.get("kind") in ("image", "pdf")]
    if seen:
        out[-1]["files"] = seen
    return out


ASK_MARK = "```ask"


def _save_state(vault, cid: str, **kw) -> None:
    from . import engine as CH

    def ch(c):
        if c.get("consortium"):
            c["consortium"].setdefault("state", {}).update(kw)

    CH.modify_chat(vault, cid, ch)


def run(
    vault,
    chat: dict,
    g: dict,
    text: str,
    web: bool = False,
    terms: bool = False,
    start: tuple = (0, 0),
    summary_only: bool = False,
) -> None:
    """The discussion itself, in the generation thread. g is the live state the UI polls."""
    from . import engine as CH
    from . import terms as TM

    cid = chat["id"]
    web_note = ""
    web_hid: dict = {}  # secrets cut from the shared search query: shown on the first message
    if web and not summary_only:
        from . import economy as EC

        found = EC.web_context(text, True)
        g["sources"] = found["sources"]
        if found.get("searched"):
            from .. import outgoing as OG

            OG.log(
                vault,
                "web",
                "",
                len(found.get("query", "")),
                found.get("redacted") or {},
                {"purpose": "поиск в интернете", "chat": cid, "web": True},
            )
            web_hid.update(found.get("redacted") or {})
        if found["context"]:
            web_note = "\n\n" + CH.WEB_NOTE + "\n" + found["context"]
    joined = ""
    ch = chat["consortium"].get("challenge")
    if ch:
        joined = CHALLENGE.format(model=speaker_name(ch["by"]), answer=ch["answer"])
    elif chat["consortium"].get("from") and not (chat["consortium"].get("state") or {}).get("spoke"):
        joined = JOINED.format(model=speaker_name(chat["consortium"]["from"]))

    def speak(ref: str, r: int, names: dict, rounds: int, final: bool) -> str:
        pid, mname = CH.split_model(ref)
        me = names[ref]
        cfg = CH.load_chat(vault, cid).get("consortium") or chat["consortium"]
        fmt = cfg.get("format", "council")
        words, fwords = LENGTHS.get(cfg.get("length"), LENGTHS["normal"])
        role = ROLES.get((cfg.get("roles") or {}).get(ref, ""), "")
        side = side_of(cfg, ref)
        extra = (f"\n- Твоя роль — {role}. Смотри на вопрос с этой стороны." if role else "") + (
            f"\n- Твоя сторона в дебатах: {side}." if side and not final else ""
        )
        look = bool(cfg.get("search", True))
        own_sources: list = []
        g.update(text="", speaker=me, speaker_ref=ref, pid=pid, phase="пишу", who=me, usage={})

        def say(sysm: str, msgs: list, prefix: str = "") -> str:
            """One pass of the speaker. A reply that may be a «[поиск: …]» line is not shown while it streams."""
            buf, use = "", {}
            for piece in PR.stream(
                vault,
                pid,
                mname,
                sysm,
                msgs,
                stop=lambda: g["stop"] or g.get("cut"),
                usage=use,
                meta={"purpose": "консорциум", "chat": cid},
            ):
                buf += piece
                lead = buf.lstrip()
                if look and ("[поиск:".startswith(lead[:7]) or lead.startswith("[поиск")):
                    continue
                g["text"] = prefix + buf
            for k, v in use.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    g["usage"][k] = g["usage"].get(k, 0) + v
            hid_add(use.get("redacted"))
            return buf

        def hid_add(red: dict | None) -> None:
            """Secrets cut before this speaker's requests left: the quiet lock under its message counts them."""
            for k, v in (red or {}).items():
                hid[k] = hid.get(k, 0) + v

        hid: dict = {}
        if web_hid:
            hid_add(web_hid)
            web_hid.clear()

        try:
            stage = STAGES[stage_of(min(r, rounds - 1), rounds, fmt)]
            head = CH.system_prompt(vault, pid, log=False, query=text, model=mname)
            head += f"\n\nТы подключён через {PR.PROVIDERS[pid]['name']}"
            head += f", модель {mname or PR.PROVIDERS[pid]['name']}." if mname else "."
            from . import tools as TL
            from ..agent import profile as P
            from .. import mcp_server as MC

            can_act = TL.enabled(vault) and not P.load(vault).get("tools_ask", False)
            if can_act:
                head += "\n\n" + TL.rule(vault)
                if pid == "harness":
                    head += (
                        "\n\nСвоих инструментов у тебя нет — только действия Mnemai блоками ```mnema. "
                        "Не отвечай «у меня нет инструментов»."
                    )

            def build(rule: str, found: str = "") -> str:
                return (
                    head
                    + "\n\n"
                    + RULES.format(
                        names=", ".join(names.values()),
                        me=me,
                        question=(text or "")[:1500],
                        stage=f"Сейчас круг {r + 1} из {rounds}. " + stage[1],
                        joined=joined,
                        words=words,
                        role=extra,
                        search=rule,
                        final=(ROAST_FINAL if fmt == "roast" else FINAL).format(fwords=fwords) if final else "",
                    )
                    + web_note
                    + found
                    + ("\n\n" + TM.RULE if terms else "")
                )

            system = build(SEARCH_RULE if look else "")
            msgs = history(CH.load_chat(vault, cid), ref, names, text)
            if pid == "local":
                from .. import localllm

                if not localllm.server_running(mname):
                    g["phase"] = "запускаю модель на компьютере"
                localllm.ensure_server(mname, vault)
                g["phase"] = "пишу"
            raw = say(system, msgs)
            steps = 0
            while can_act and not (g["stop"] or g.get("cut")) and steps < 4:
                call = TL.parse(CH.strip_thinking(raw))
                if not call:
                    break
                steps += 1
                head_text = TL.before(CH.strip_thinking(raw), call).strip()
                g["phase"] = "делаю: " + call["tool"]
                g["text"] = head_text
                try:
                    result, line, path = MC.run_action(vault, call, PR.PROVIDERS[pid]["client"])
                except Exception as e:  # a failed action must not kill the speaker
                    result, line = f"Не получилось: {str(e)[:300]}", ""
                if line:
                    act = {
                        "role": "assistant",
                        "kind": "action",
                        "ts": CH._now(),
                        **CH._action_view(call, line, path, result),
                        "model": ref,
                        "speaker": me,
                        "round": r + 1,
                    }
                    CH.modify_chat(vault, cid, lambda c: (c["messages"].append(act), c.update(updated=CH._now())))
                msgs = msgs + [
                    {
                        "role": "assistant",
                        "text": head_text
                        + f"\n[action: {call['tool']} {call.get('path') or call.get('command') or ''}]",
                    },
                    {"role": "user", "text": "[Результат действия от Mnemai]\n" + result},
                ]
                g["phase"] = "пишу"
                raw = say(system, msgs, prefix=(head_text + "\n\n") if head_text else "")
            queries = SEARCH_RE.findall(CH.strip_thinking(raw))[:MAX_SEARCHES] if look else []
            if queries and not (g["stop"] or g.get("cut")):
                g.update(phase="ищу в интернете", text="", searching=queries)
                found = lookup(queries, vault=vault, chat=cid)
                hid_add(found.get("redacted"))
                own_sources = found["sources"]
                g.update(phase="пишу", searching=[])
                more = (
                    SEARCH_DONE.format(queries="; ".join(queries), context=found["context"])
                    if found["context"]
                    else "\n\n[Поиск ничего не дал. Новых запросов не делай: ответь из своих знаний и скажи, "
                    "что подтвердить не удалось.]"
                )
                raw = say(build("", more), msgs)  # the second pass has no search rule: it answers
                if not SEARCH_RE.sub("", raw).strip() and not (g["stop"] or g.get("cut")):
                    raw = say(build("", more) + "\n\nОтветь сейчас, без строк [поиск: …].", msgs)
            raw = SEARCH_RE.sub("", raw)
            g["text"] = raw
            answer, glossary = TM.split(CH.strip_tool_markup(CH.strip_thinking(raw)).strip())
            err = ""
        except Exception as e:
            from .. import errors as E

            answer, err, glossary = "", E.human(e, me, mname, E.vpn_name(vault)), []
            if E.account_problem(e):  # no key or no money: it sits out the rest of the discussion
                if ref not in g.setdefault("dropped", []):
                    g["dropped"].append(ref)
                err += " Дальше обсуждают без него."
            elif any(m.get("model") == ref and m.get("error") for m in CH.load_chat(vault, cid)["messages"][-6:]):
                g.setdefault("dropped", []).append(ref)  # failed twice in a row: out
        if g.get("abandoned") or (not answer and not err):  # cut before saying anything, or dropped
            g["text"] = ""
            return ""
        msg = {
            "role": "assistant",
            "text": answer,
            "ts": CH._now(),
            "model": ref,
            "speaker": me,
            "round": r + 1,
            "stage": "Итог" if final else STAGES[stage_of(min(r, rounds - 1), rounds, fmt)][0],
            "tokens": {k: v for k, v in g["usage"].items() if k not in ("progress", "reasoning", "redacted")},
        }
        if hid:
            msg["redacted"] = hid
        if err:
            msg["error"] = err
        if (g["stop"] or g.get("cut")) and answer:
            msg["cut"] = True  # interrupted by the owner
        if glossary:
            msg["terms"] = glossary
        if final and answer:
            msg["summary"] = True
        if own_sources:
            msg["sources"] = own_sources
            msg["searched"] = True
        elif final and g.get("sources"):
            msg["sources"] = g["sources"]

        def add(c):
            c["messages"].append(msg)
            c["updated"] = CH._now()
            if c.get("consortium"):
                c["consortium"].setdefault("state", {})["spoke"] = True

        CH.modify_chat(vault, cid, add)
        g["seq"] = g.get("seq", 0) + 1
        if answer:
            from .. import achievements as ACH

            ACH.event(vault, "answer", pid=pid, terms=len(glossary))
        g["text"] = ""
        return answer

    r, i = start
    while not summary_only:
        cfg = CH.load_chat(vault, cid).get("consortium") or chat["consortium"]  # the owner may change it as they talk
        members, rounds = cfg["members"], cfg["rounds"]
        names = names_for(members)
        if i >= len(members):
            r, i = r + 1, 0
        if r >= rounds:
            _save_state(vault, cid, status="done", round=0, next=0)
            g["status"] = "done"
            return
        if g["stop"]:  # the owner wrote: his message goes on from here
            _save_state(vault, cid, status="running", round=r, next=i)
            return
        if g.get("finish"):
            break
        if g.get("pause"):
            _save_state(vault, cid, status="paused", round=r, next=i)
            g["status"] = "paused"
            return
        ref = order(cfg, r)[i]
        final = r == rounds - 1 and i == len(members) - 1 and len(members) * rounds > 1
        dropped = g.get("dropped", [])
        alive = [m for m in members if m not in dropped]
        if not alive:
            g["error"] = "Никто из участников не может ответить: проверь ключи и баланс — Настройки → ИИ и модели."
            _save_state(vault, cid, status="done", round=0, next=0)
            g["status"] = "done"
            return
        if ref in dropped:
            if not final:
                i += 1
                continue
            ref = cfg.get("summarizer") if cfg.get("summarizer") in alive else alive[-1]  # the summary still comes
        nxt = "" if final else names[order(cfg, r)[i + 1] if i + 1 < len(members) else order(cfg, r + 1)[0]]
        g.update(
            status="running",
            round=r + 1,
            rounds=rounds,
            members=[names[m] for m in members],
            idx=i,
            next=nxt,
            turn=r * len(members) + i + 1,
            turns=len(members) * rounds,
        )
        _save_state(vault, cid, status="running", round=r, next=i)
        answer = speak(ref, r, names, rounds, final)
        if g.get("pause") and not answer:  # stopped before a word: on «Продолжить» the same one speaks
            continue
        if g.get("pause") and final:  # the last word cut: a pause, not the end — «Продолжить» lets him finish
            _save_state(vault, cid, status="paused", round=r, next=i)
            g["status"] = "paused"
            return
        if final and not answer and not g["stop"] and not g.get("pause"):
            alt = next((m for m in members if m != ref and m not in g.get("dropped", [])), None)
            if alt:  # the one summing up failed: another one does it
                answer = speak(alt, r, names, rounds, True)
        i += 1
        _save_state(vault, cid, round=r, next=i)
        if final:
            _save_state(vault, cid, status="done", round=0, next=0)
            g["status"] = "done"
            return
        if answer and ASK_MARK in answer and not g.get("finish"):  # a question to the owner: the others wait
            _save_state(vault, cid, status="waiting", round=r, next=i, asked=names[ref])
            g["status"] = "waiting"
            return
    # «Завершить»: one AI sums up right away — the one whose turn it would be
    g.update(cut=False, stop=False, status="summary")
    cfg = CH.load_chat(vault, cid)["consortium"]
    members = cfg["members"]
    names = names_for(members)
    alive = [m for m in members if m not in g.get("dropped", [])] or members
    ref = cfg.get("summarizer") if cfg.get("summarizer") in alive else alive[i % len(alive)]
    g.update(round=r + 1, rounds=cfg["rounds"], members=[names[m] for m in members], idx=members.index(ref), next="")
    speak(ref, r, names, cfg["rounds"], True)
    _save_state(vault, cid, status="done", round=0, next=0)
    g["status"] = "done"


def lookup(queries: list[str], budget: int = 6000, vault=None, chat: str = "") -> dict:
    """The speaker's own queries: pages for each, numbered as one list of sources. A query is cleaned of secrets and
    written to «Что ушло наружу» like any request that leaves the computer."""
    from .. import outgoing as OG, web

    blocks, sources, hidden = [], [], {}
    for q in queries:
        red = OG.Redactor()
        q = OG.LABEL_RE.sub(" ", red.apply(q)).strip()
        for k, v in red.summary().items():
            hidden[k] = hidden.get(k, 0) + v
        if not q:
            continue
        if vault is not None:
            OG.log(vault, "web", "", len(q), red.summary(), {"purpose": "поиск в интернете", "chat": chat, "web": True})
        try:
            found = web.gather(q, pages=3, budget=budget // max(1, len(queries)))
        except Exception:
            continue
        off = len(sources)
        if found["context"]:
            blocks.append(re.sub(r"^\[(\d+)\]", lambda m: f"[{int(m.group(1)) + off}]", found["context"], flags=re.M))
        sources += found["sources"]
    return {"context": "\n\n".join(blocks), "sources": sources, "redacted": hidden}


def wait_stopped(g: dict, timeout: float = 20.0) -> None:
    """The owner stepped in: a speaker in the middle of a sentence finishes it; one that has not said a word yet
    (a slow or hung service) is dropped at once — whatever it says later is thrown away."""
    g["stop"] = True
    if not (g.get("text") or "").strip():
        g["abandoned"] = True
        return
    t = time.time()
    while not g.get("done") and time.time() - t < timeout:
        time.sleep(0.1)


def resume_point(chat: dict) -> tuple:
    """Where the next words come from: a paused, waiting or interrupted discussion goes on from the next speaker,
    a finished one starts anew."""
    st = (chat.get("consortium") or {}).get("state") or {}
    if st.get("status") in ("running", "paused", "waiting"):
        return int(st.get("round", 0)), int(st.get("next", 0))
    return 0, 0


def start(
    vault,
    chat: dict,
    text: str,
    sync: bool,
    web: bool,
    terms: bool = False,
    at: tuple | None = None,
    summary_only: bool = False,
) -> dict:
    from . import engine as CH

    at = resume_point(chat) if at is None else at
    g = {
        "text": "",
        "done": False,
        "error": "",
        "phase": "думаю",
        "stop": False,
        "pid": "",
        "consortium": True,
        "seq": 0,
        "speaker": "",
        "usage": {},
        "status": "running",
        "pause": False,
        "finish": False,
        "cut": False,
    }
    CH._gen[chat["id"]] = g

    from .. import achievements as ACH

    if len([m for m in CH.load_chat(vault, chat["id"])["messages"] if m["role"] == "user"]) == 1:
        ACH.event(vault, "consortium", members=chat["consortium"]["members"], rounds=chat["consortium"]["rounds"])

    def work():
        try:
            run(vault, chat, g, text, web, terms, at, summary_only)
        except Exception as e:
            g["error"] = str(e)[:400]
        finally:
            g["phase"] = ""
            g["done"] = True
            c = CH.load_chat(vault, chat["id"])
            if not c.get("title_manual") and not c.get("title_auto"):
                first = chat["consortium"]["members"][0]
                pid, mname = CH.split_model(first)
                threading.Thread(target=CH._auto_title, args=(vault, chat["id"], pid, mname), daemon=True).start()

    if sync:
        work()
    else:
        threading.Thread(target=work, daemon=True, name="mnema-consortium").start()
    return {"chat": chat["id"], "title": chat["title"], "model": "consortium"}


def last_owner_text(chat: dict) -> str:
    return next((m["text"] for m in reversed(chat["messages"]) if m["role"] == "user" and m.get("text")), "")


def _set(cfg: dict, members: list | None, rounds: int | None, extra: dict | None = None) -> dict:
    keep = {
        k: v
        for k, v in (extra or {}).items()
        if k in ("format", "roles", "summarizer", "length", "search") and v is not None
    }
    return clean({**cfg, **({"members": members} if members else {}), **({"rounds": rounds} if rounds else {}), **keep})


def control(
    vault,
    cid: str,
    action: str,
    members: list | None = None,
    rounds: int | None = None,
    model: str = "",
    extra: dict | None = None,
) -> dict:
    """The round table's buttons: start (also in a conversation that is already going), pause, resume, finish,
    set (members and rounds, also while they talk), off (back to one AI)."""
    from . import engine as CH
    from ..agent import profile as P

    chat = CH.load_chat(vault, cid)
    g = CH._gen.get(cid, {})
    live = g.get("done") is False
    terms = bool(P.load(vault).get("terms", True))
    if action == "set":
        if not chat.get("consortium"):
            raise ValueError("это не консорциум")
        CH.modify_chat(vault, cid, lambda c: c.update(consortium=_set(c["consortium"], members, rounds, extra)))
        return CH.state(cid) if live else {"ok": True}
    if action == "pause":  # «Остановить»: the one speaking stops mid-sentence (what he said stays), the rest wait
        if live and g.get("consortium"):
            g.update(pause=True, cut=True)
        return CH.state(cid)
    if action == "finish":
        if live and g.get("consortium"):
            g.update(finish=True, cut=True)
            return CH.state(cid)
        if chat.get("consortium"):
            return start(vault, chat, last_owner_text(chat), False, False, terms, resume_point(chat), summary_only=True)
        raise ValueError("это не консорциум")
    if live:
        raise ValueError("дождись, пока договорит текущий ИИ")
    if action == "off":

        def off(c):
            was = c.pop("consortium", None) or {}
            c["model"] = model or was.get("from") or (was.get("members") or [CH.default_model(vault)])[0]
            c["messages"].append(
                {"role": "assistant", "kind": "cons_end", "text": "", "ts": CH._now(), "model": c["model"]}
            )

        CH.modify_chat(vault, cid, off)
        return {"ok": True}
    if action == "start":  # also in a conversation that is already going
        question = (((extra or {}).get("challenge") or {}).get("question") or "").strip()
        if not chat.get("consortium"):
            cfg = clean({"members": members or [], "rounds": rounds or 2, **(extra or {})})
            cfg["from"] = chat.get("model") or CH.default_model(vault)
            cfg["state"] = {"status": "running", "round": 0, "next": 0}

            def on(c):
                c["consortium"] = cfg
                c["model"] = "consortium"
                c["messages"].append(
                    {
                        "role": "assistant",
                        "kind": "cons_start",
                        "text": "",
                        "ts": CH._now(),
                        "members": cfg["members"],
                        "rounds": cfg["rounds"],
                    }
                )

            chat = CH.modify_chat(vault, cid, on)
        return start(vault, chat, question or last_owner_text(chat) or "Обсудите разговор выше.", False, False, terms)
    if action == "resume":
        return start(vault, chat, last_owner_text(chat), False, False, terms)
    raise ValueError("неизвестное действие")
