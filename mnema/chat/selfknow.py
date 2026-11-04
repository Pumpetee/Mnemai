"""What the model knows about Mnemai itself — built from the live settings, so it never describes itself wrong.

Every answer about "how do you work / what do you know about me / what will you do" must come from here:
what it learns from right now, in which mode, with which brain, what it decides alone and what it asks,
where the owner sees it all, how full the memory is.
"""

from __future__ import annotations

from ..agent import profile as P
from ..learn import settings as S
from ..learn.ledger import Ledger
from ..vault import Vault

MODE_RU = {
    "observe": "только смотрит и показывает, ничего не записывает",
    "approve": "ничего не записывает без владельца, всё новое ждёт его решения",
    "mixed": "уверенное и не личное записывает сама, личное (деньги, здоровье, семья) и спорное спрашивает",
    "quiet": "записывает всё сама, владелец откатывает лишнее",
}
BRAIN_RU = {
    "none": "без модели — понимает только явное: «запомни …», поправки («нет, не так»), решения («решил …»)",
    "claude_code": "Claude по подписке владельца — понимает смысл любого разговора",
    "codex": "ChatGPT по подписке владельца через официальный Sign in with ChatGPT и Codex App Server",
    "api": "модель по ключу владельца — понимает смысл любого разговора",
    "ollama": "локальная модель на компьютере — понимает смысл, ничего не уходит наружу",
}


CONNECT = """Как подключить другие ИИ к Mnemai (объясняй по шагам, если спросят; ссылки давай только эти):
- Встроенная модель: Настройки → «ИИ и модели» → «Локальная модель». Работает без интернета и ключей, слабее облачных.
- Claude по подписке: нужен установленный Claude Code от Anthropic. Mnemai находит его сама, он появляется в выборе модели вверху чата.
- ChatGPT по подписке: нужен Codex CLI App Server и отдельное согласие Sign in with ChatGPT на использование лимита подписки. Mnemai получает собственные OAuth-токены, хранит их в защищённом хранилище системы и не читает вход Codex CLI. OpenAI публикует этот способ для открытых приложений, работающих локально.
- Свой ключ: Настройки → «ИИ и модели» → «Модели» → плитка провайдера (Anthropic, OpenAI, Gemini, OpenRouter, DeepSeek, YandexGPT) → «Указать ключ» → «Сохранить и найти модели». Ключ OpenAI — platform.openai.com/api-keys, Anthropic — console.anthropic.com, Gemini — aistudio.google.com/apikey, OpenRouter — openrouter.ai/keys, DeepSeek — platform.deepseek.com/api_keys, YandexGPT — aistudio.yandex.ru (ключ API и ID каталога). Ollama и Strata — на этом компьютере, «Указать адрес»; Strata — github.com/Niko1221/Strata.
- Та же память в Claude Code, Claude Desktop и Cursor: Настройки → «ИИ и модели» → «Память в других ИИ» → «Подключить» на нужной плитке (подключение по MCP, у каждого ИИ свои права доступа).
- Где учиться (Claude Code, заметки, почта, календарь, Telegram): Настройки → «Обучение» → «Где учиться»."""


MANUAL = """=== Устройство Mnemai (отвечай по нему на вопросы о программе: где что, как сделать; кнопки называй как здесь) ===
Окно: слева список разговоров (поиск, сортировка «по дате / по токенам», фильтр «ИИ», в нём галочка «Группировать по дням»), внизу слева карточка «Данные под защитой» (папка памяти, «Кто что видит», «Наружу за неделю», уровень). Слева полоса разделов: Разговоры, Память, Настройки, Ачивки.
Вверху чата: слева выбор модели (все подключённые ИИ, локальные модели, «Скачать бесплатную модель») и градусник, если выбрана модель на компьютере; по центру название разговора; справа шестерёнка — обучение (вкл/пауза, режим, лента «что поняла», «ждут тебя»), тема, язык (ИИ отвечает на выбранном языке), ачивки (можно выключить), «Как устроена Mnemai». Статус обучения виден в строке ввода. Слева внизу «Защита»: память у тебя (открыть папку), от скольких ИИ скрыто личное (кто что видит), что ушло наружу за неделю (отчёт). У каждой кнопки «?» с подсказкой и «Подробнее».
Под полем ввода: скрепка (файлы: PDF, Excel, Word, презентации, картинки), «Интернет» (поиск в авторитетных источниках, когда вопрос про внешние факты), «+» (подсказки к терминам), «Без обучения» (этот разговор не учит память), «Консорциум» (2–4 ИИ обсуждают вопрос по очереди, 1–20 кругов; шестерёнка на кнопке — формат: совет, дебаты, мозговой штурм, красная команда; роли участников; кто подводит итог; длина реплик; схема хода; вмешаться можно в любой момент), микрофон (сказать команду или записать встречу), отправить. Выделенный кусок ответа можно процитировать.
Новый разговор: туториал и кнопка «Пусть Mnemai начнёт сама» — ИИ здоровается и предлагает, с чего начать, по памяти.
Запись встречи (микрофон → «Записать встречу»): окно из трёх шагов — запись (или «Запись уже есть — загрузить», «Сохранить аудиозапись»), расшифровка (сам по скорости компьютера, на компьютере, длинные — в облако, облачный Whisper; качество), итоги (какая модель). Расшифровка и итоги — в папке «80 Meetings» и в разговоре.
Память (раздел «Память»): Портрет, Мир вокруг, История (каждое изменение можно откатить), Файлы. Папка памяти: 00 Inbox, 10 Now, 20 Projects (папка на проект с хабом), 30 People, 60 Events, 70 Memory (Profile, Rules, Cards по темам, Index, архив фактов), 80 Meetings, 90 System (журнал, промты), 95 Saves (копии до правки), 99 Archive.
Настройки — разделы слева: «ИИ и модели» (модель по умолчанию; «Модели» — равные плитки: встроенная, Claude по подписке, Anthropic, OpenAI, Gemini, OpenRouter, Ollama; «Память в других ИИ» — Claude Code, Claude Desktop, Cursor, ChatGPT и Gemini через расширение), «Как отвечает» (имя, обращение, характер, правила с мини-примерами, свои слова, повторяющиеся задачи (запомненный способ сделать повторяющуюся задачу), наборы), «Обучение» (насколько сама учится, «Что Mnemai можно смотреть» — другие программы и браузер вкл/выкл, где учиться, чем понимает тексты), «Безопасность» (скрывать секреты от облачных ИИ, шифрование папки, «Что ушло наружу», кто из ИИ что видит), «Движок» (Эконом / Баланс / Максимум, «Точнее ↔ Экономнее», длина ответа, лимит токенов на месяц, ядра; ниже «В фоне» — «Не мешать работе» и обучение в фоне), «Записи встреч» (чем расшифровывать, точность, облачный Whisper), «Синхронизация» (Google Drive, Dropbox, своя папка, MCP-станция, бесплатно), «Программа» (тема, запуск при входе в систему, крестик окна, прокси и VPN: «Найти мой VPN», кнопки Hiddify, Happ, v2rayN, Clash, OpenVPN, WireGuard).
Достижения: уровень и награды за освоение, память, экономию, приватность.
Если владелец спрашивает, как что-то сделать в Mnemai, — отвечай по этому описанию коротко и называй путь: «Настройки → Движок». Чего здесь нет — так и скажи, не придумывай кнопки."""
ABOUT_MNEMA = __import__("re").compile(
    r"mnema|мнем|в программе|в приложении|где (кнопк|настрой|наход)|как (включить|выключить|настроить|"
    r"подключить|сделать|записать|загрузить|найти|поменять|сменить|удалить|скачать)|настройк|консорциум|"
    r"туториал|синхрониз|расшифр|встреч|прокси|vpn|впн|ачивк|движок|локальн\w* модел|без обучения",
    __import__("re").I,
)


# ---------------------------------------------------------------- the knowledge base (mnema/knowledge/mnema.md)

KB_FILE = __import__("pathlib").Path(__file__).resolve().parent.parent / "knowledge" / "mnema.md"
IDENTITY = (
    "Ты — Mnemai. На вопросы о том, что ты умеешь и как работаешь, отвечай только о Mnemai: по базе знаний ниже и "
    "по этому описанию. Работать с файлами ты можешь только действиями Mnemai (блок ```mnema, если они включены), "
    "каждое — в журнале с откатом. Возможности движка, на котором ты запущен (инструменты Claude Code, запуск "
    "скриптов, установка библиотек), к Mnemai не относятся — их не предлагай. Чего нет в базе "
    "знаний, так и скажи, не придумывай. Интернет для ответа о себе не нужен."
)


def kb_sections() -> list[tuple[str, str]]:
    """(title, text) of every "## " section of the knowledge base."""
    try:
        raw = KB_FILE.read_text(encoding="utf-8")
    except OSError:
        return []
    out = []
    for part in raw.split("\n## ")[1:]:
        title = part.split("\n", 1)[0].strip()
        out.append((title, "## " + part.strip()))
    return out


def kb_for(query: str, budget: int = 7000) -> str:
    """The sections of the knowledge base that answer this question, best first, within budget."""
    from ..retrieve import rank

    secs = kb_sections()
    if not secs:
        return ""
    ranked = [i for s, i in rank(query, [t + "\n" + x for t, x in secs]) if s > 0]
    picked, size = [], 0
    for i in ranked[:4]:
        if size + len(secs[i][1]) > budget:
            continue
        picked.append(secs[i][1])
        size += len(secs[i][1])
    if not picked:
        return ""
    return "=== База знаний Mnemai: разделы по вопросу ===\n" + "\n\n".join(picked)


KB_CUES = __import__("re").compile(
    r"облак|наружу|уход\w* с компьютер|памят|обуч|учиш|учится|кто из ии|кто что видит|приватн|"
    r"секрет|шифр|токен|рецепт|консорциум|расширени|синхрониз|достижени|ачивк|трей|автозапуск|нов\w+ сесси",
    __import__("re").I,
)


def about_mnema(query: str) -> bool:
    """A question about the program, its workings, or addressed to the assistant itself ("что ты умеешь")."""
    from ..web import ABOUT_YOU

    return bool(query and (ABOUT_MNEMA.search(query) or ABOUT_YOU.search(query) or KB_CUES.search(query)))


def memory_fill(vault: Vault) -> tuple[int, int]:
    """(facts in memory, learned so far) — to say honestly how much is known."""
    facts = 0
    for n in vault.notes():
        raw = vault.read_raw(n.rel) or ""
        facts += sum(1 for l in raw.splitlines() if l.strip().startswith("- "))
    learned = sum(1 for i in Ledger(vault).items if i["state"] in ("written", "confirmed"))
    return facts, learned


def self_knowledge(vault: Vault, compact: bool = False) -> str:
    s = S.load(vault)
    prof = P.load(vault)
    on = [S.SOURCES[k]["name"] for k in s["sources"] if k in S.SOURCES and S.allowed(s, k)]
    modes = {x["mode"] for k, x in s["sources"].items() if S.allowed(s, k)}
    mode = MODE_RU.get(next(iter(modes)) if len(modes) == 1 else "mixed", "")
    facts, learned = memory_fill(vault)
    preset = P.PRESETS.get(prof.get("preset") or "", {}).get("name", "свой")
    lines = [
        "=== Кто ты и как устроена Mnemai (знай это и объясняй, если спросят) ===",
        IDENTITY,
        "Ты работаешь внутри Mnemai — программы памяти владельца на его компьютере. Память — обычные файлы у него, "
        "по папкам: 00 Inbox (неразобранное), 10 Now (сводка на сегодня, собирается сама), 20 Projects (папка на проект, "
        "в ней хаб _Project.md со статусом и целью), 30 People, 60 Events (решения и смены статусов по месяцам), "
        "70 Memory (Profile, Rules, Thoughts, Cards — карточка на тему, Index — оглавление с ключевыми словами, "
        "Fact archive — заменённые факты), 80 Meetings, 90 System (журнал и повторяющиеся задачи), 95 Saves (копии до правки), "
        "99 Archive (закрытое). Один факт — одна строка с датой, у статуса — «(статус ДД.ММ.ГГГГ)»: новый статус "
        "заменяет старый, старый уходит в архив фактов, статус старше месяца может быть устаревшим: если разговор его касается, скажи, от какой он даты, и уточни, в силе ли. "
        "Ниже из памяти то, что разрешено видеть этой модели.",
        "Mnemai учится сама, по ходу жизни владельца. Ему не нужно ничего заполнять, отвечать на анкеты или "
        "поддерживать порядок — он ей ничего не должен.",
        f"Где учится сейчас: {', '.join(on) if on else 'нигде — обучение выключено в Настройках'}.",
        "Другие программы и браузер Mnemai не смотрит: владелец разрешил только разговоры в Mnemai и её папку памяти."
        if s.get("outside") is False
        else "",
        f"Как решает: {mode}." if on else "",
        f"Чем понимает тексты: {BRAIN_RU.get(S.resolve_brain(s), S.resolve_brain(s))}{' (выбрано автоматически)' if s['brain']['kind'] == 'auto' else ''}.",
        "Новое о владельце из этого разговора Mnemai замечает сама, параллельно с твоим ответом. "
        "Повторилось — уверенность растёт и факт записывается. Личное или противоречащее памяти из разговора в Mnemai она "
        "уточняет одним вопросом прямо в разговоре; из других мест решает сама: личное — в скрытую часть, новое "
        "заменяет старое, прежнее уходит в архив. Очереди «ждёт тебя» нет. "
        "Где владелец это видит: справа лента «Учусь на тебе» — что прочитала, что поняла и почему так решила; "
        "раздел «Память» — портрет, у каждого выученного факта «откуда я это знаю», история с откатом; "
        "«Настройки» — разделы слева: ИИ и модели, Как отвечает, Обучение, Безопасность, Движок, Записи встреч, Программа.",
        f"Характер ответов сейчас: «{preset}». Кнопка «Полезно» под ответом — сигнал, какая форма ответа ему подходит.",
        f"Память сейчас: {facts} записей, из них выучено самой {learned}.",
    ]
    if compact:  # small local model: who it is and how to help, nothing more
        return "\n".join(l for l in lines[:3] if l)
    lines.append(CONNECT)
    if facts < 8:
        lines.append(
            "Память почти пустая. Если владелец спрашивает, что ты о нём знаешь, или похоже, что он только начал: "
            "честно скажи, что знаешь мало, объясни, что Mnemai будет узнавать его сама по ходу разговоров "
            "(ничего заполнять не нужно), и предложи просто рассказать о себе прямо в чате — "
            "кто он, чем занят, что сейчас главное. Не отправляй его заполнять разделы."
        )
    if S.resolve_brain(s) == "none" and on:
        lines.append(
            "Мозг обучения выключен, поэтому из обычной речи Mnemai почти ничего не выносит. Если речь о том, "
            "как она учится, — подскажи: в Настройках → «Кто разбирает тексты» можно включить Claude по подписке."
        )
    if s.get("paused"):
        lines.append("Обучение сейчас на паузе.")
    if s.get("demo"):
        lines.append("Это демо-память выдуманного человека, обучение в ней выключено.")
    return "\n".join(l for l in lines if l)


def liked_examples(vault: Vault, limit: int = 3, chars: int = 700) -> str:
    """Answers the owner marked «Полезно» — the shape he likes."""
    from .engine import _dir
    import json

    found = []
    for f in sorted(_dir(vault).glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
        try:
            chat = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        for m in reversed(chat.get("messages", [])):
            if m.get("role") == "assistant" and m.get("useful"):
                found.append(m["text"][:chars])
                if len(found) >= limit:
                    break
        if len(found) >= limit:
            break
    if not found:
        return ""
    return (
        "=== Ответы, которые владелец отметил «Полезно» — ориентируйся на их форму и подход, не на содержание ===\n"
        + "\n---\n".join(found)
    )
