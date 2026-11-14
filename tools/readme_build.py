"""The README in nine languages, built from one layout: a centered header with the animated logo and a typing line,
badges, a button to the guide, the languages with their README and guide, downloads, animations of the real
interface, the AIs it works with, the details folded.

    python tools/readme_build.py               →  README.md (English), README.<lang>.md
    python tools/readme_build.py --translate   →  first translates what is missing for the other eight languages

English and Russian are written here (L). The other languages are translated from English by the owner's
Claude Code into docs/readme/<lang>/strings.json and docs/readme/<lang>/<part>.md, once; delete a file to have it
translated again. The long parts (install, build, how it is built, security, license) live in docs/readme/<lang>/.
Animations are recorded in every language by tools/qa/readme_anim.py.
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
REPO = "Pumpetee/Mnemai"


def section(text: str, title: str) -> str:
    """The body of one «## title» section of a README, without its heading."""
    m = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    if not m:
        raise SystemExit(f"нет раздела «{title}»")
    return m.group(1).strip()


def typing(lines: list[str], color="A78BFA") -> str:
    q = ";".join(quote(x, safe="") for x in lines)
    return (
        "https://readme-typing-svg.demolab.com?font=Inter&weight=700&size=26&duration=2600&pause=900"
        f"&color={color}&center=true&vCenter=true&width=720&height=46&lines={q}"
    )


def badge(label: str, msg: str, color: str, logo: str = "", style: str = "flat-square") -> str:
    e = lambda s: quote(s.replace("-", "--").replace("_", "__"), safe="")  # noqa: E731
    url = f"https://img.shields.io/badge/{e(label)}-{e(msg)}-{color}?style={style}"
    if logo:
        url += f"&logo={logo}&logoColor=white"
    return url


def tile(name: str, label: str, src: str) -> str:
    return f'<td align="center" width="92"><img src="{src}" width="40" alt="{label}"><br><sub><b>{label}</b></sub></td>'


SI = "https://cdn.simpleicons.org"

L = {
    "en": {
        "file": "README.md",
        "langs_intro": "Mnemai speaks nine languages. The interface, the help and the AI's answers follow the one you pick, even when you write in another. This README and the Mnemai guide exist in each of them.",
        "qr": "Scan to open the repository",
        "guide_btn": "Mnemai guide",
        "guide_msg": "every screen and setting",
        "badges": ["read only", "read only", "encryption", "your files"],
        "typing": [
            "One memory for every AI",
            "Free, on your computer, no account",
        ],
        "lead": "Mnemai remembers who you are, what you are working on, what you decided and how you like answers — and every AI you talk to gets that context. The memory is a folder of plain Markdown files on your computer. No cloud, no account.",
        "dl": ("Download for", "all files"),
        "hero_alt": "A question, and the answer comes from memory: the week plan as a table, with the price and the meeting rule it already knows",
        "hero_cap": "You ask «what matters this week?» — the plan comes as a table, with the agreed price and your rule about meetings. You never retyped them.",
        "langs": "Languages",
        "what": "What it does",
        "grid": [
            ("🧠", "Knows you", "A portrait every AI reads first, a living memory map, plain files you own."),
            ("🗣️", "Consortium", "Claude, ChatGPT and Gemini argue and agree on one answer."),
            ("🎙️", "Meetings", "A call becomes a transcript, a summary and tasks with owners."),
            ("🔐", "Private", "A password on the memory like KeePass. Secrets never reach the cloud."),
            ("💻", "Offline", "13 free models run on your computer, with no keys."),
            ("📉", "Fewer tokens", "Only what matters goes to the model: 4.8× fewer tokens on a long contract."),
        ],
        "sec": [
            (
                "🧠 It knows you",
                "memory",
                "Portrait and memory map: topics as bubbles, the size is how much Mnemai knows",
                [
                    "**A portrait every AI reads first:** who you are, what you are building, how you like to work. Mnemai writes it as it learns, you can fix it by hand.",
                    "**A memory map:** each topic is a bubble, a pulse means it changed recently, a lock means some AIs don't see it.",
                    "**Old facts don't pass for new ones:** every fact carries its date, and Mnemai asks again about a status older than a month.",
                    "**More than one folder:** connect an Obsidian vault or a team folder — read only, the program itself blocks writing there.",
                ],
            ),
            (
                "🗣️ Consortium: several AIs, one answer",
                "consortium",
                "Claude, ChatGPT and Gemini discuss the question, one of them sums up",
                [
                    "**Council, debate, brainstorm, red team, roast** — pick the format and the number of rounds.",
                    "**Step in at any time:** «Stop» cuts the current AI and keeps what it said.",
                    "**Argue with different AIs** under any answer: its author defends it, the rest look for where it is wrong.",
                ],
            ),
            (
                "🎙️ Meetings: from a call to tasks",
                "meetings",
                "The way a meeting goes: recording, transcript, summary, memory — each step with its own settings",
                [
                    "**Two tracks:** your microphone and the computer's sound, so the transcript knows who spoke.",
                    "**Whisper on your computer for free**, or the cloud Whisper (≈ $0.36 an hour) — silence, made-up phrases and echo are cut out.",
                    "**The summary:** what was decided, the tasks and who owns them, by any model you pick, a local one included.",
                    "**Presets:** Private, Balanced, Fast set the whole way at once.",
                ],
            ),
            (
                "🌱 It learns by itself",
                "learning",
                "You mention something in passing, and the feed shows what Mnemai read, understood and wrote down, and why",
                [
                    "**Sure means saved:** a fact it is sure of (80% or more) is written at once, a doubtful one waits to be heard again.",
                    "**Personal goes apart:** money, health and private matters land in tagged cards you can hide from any AI.",
                    "**Nothing is hidden from you:** the «What I understood and why» feed shows every decision with its reason.",
                ],
            ),
            (
                "✈️ Reads Telegram, never writes there",
                "telegram",
                "Telegram connected read only: you pick the chats, Mnemai learns from them",
                [
                    "**You pick the chats:** Mnemai learns about you and the people around you only from those.",
                    "**Read only, by design:** the Telegram client inside Mnemai can only read; any other command is refused before it is sent.",
                    "**Stays on your computer:** the login is encrypted in the system's store, and Mnemai has no servers of its own.",
                ],
            ),
            (
                "📉 Saves tokens",
                "tokens",
                "A question about a 153,000-character contract: 29,643 input tokens for the whole text, 6,159 with Mnemai",
                [
                    "**Only what matters goes out:** memory, documents and web pages are read on your computer, and the model gets the relevant parts.",
                    "**Measured:** on a question about a 153,000-character contract the whole text took 29,643 input tokens; Mnemai sent 6,159, and only the Mnemai answer was right.",
                    "**Visible every time:** under each answer you see how many tokens were saved.",
                ],
                560,
            ),
        ],
        "priv": "🔐 Private by design",
        "priv_l": ("lock", "First start: a password on the memory, like KeePass"),
        "priv_r": ("privacy", "Who sees what: a tick per part of memory, a lock per topic"),
        "priv_text": [
            "**A password on the memory:** AES-256, the key comes from your password, open-source cryptography. Without it the notes can't be read, even copied off the disk. A synced copy stays encrypted too.",
            "**Secrets stay with you:** card numbers, passwords, keys and phones become labels before anything goes to a cloud model.",
            "**Every AI has its own access:** money, health and private topics are hidden from any of them in one click.",
        ],
        "works": "🤖 Works with",
        "works_note": "The official Sign in with ChatGPT window connects the ChatGPT subscription, with a separate consent for using the plan's limit; generation runs through the Codex App Server. OpenCode Go connects with its subscription key.",
        "groups": [
            ("Cloud AI", "by key or subscription"),
            ("On your computer", "free, offline"),
            ("In your tools", "over MCP"),
            ("Systems", "one app"),
        ],
        "local": "Built-in",
        "more": "And more",
        "more_text": [
            "**Works with your files.** Reads scans, writes notes, makes PDF, Word and Excel, merges and splits PDF. Every write can be undone in Memory → History.",
            "**Commands without a model.** «Open Wikipedia with the word …», «open YouTube», «open this site» and other one-off requests run at once, without asking an AI — the same on every model.",
            "**The administrator password stays in the chat.** sudo and installing need no terminal window: Mnemai asks for the password right in the conversation, once, and neither the chat file nor a model ever sees it.",
            "**Nine languages.** The interface and the AI's answers follow the one you pick, even when you write in another.",
        ],
        "fold": ["Install", "Build from source", "How it is built", "Security"],
        "lic": "License",
        "foot": "If Mnemai remembers something useful for you, a ⭐ helps others find it.",
    },
    "ru": {
        "file": "README.ru.md",
        "langs_intro": "Mnemai говорит на девяти языках. Интерфейс, подсказки и ответы ИИ идут на выбранном, даже если пишешь на другом. Этот README и справочник Mnemai есть на каждом из них.",
        "qr": "Наведи камеру, чтобы открыть репозиторий",
        "guide_btn": "Справочник Mnemai",
        "guide_msg": "каждый экран и настройка",
        "badges": ["только чтение", "только чтение", "шифрование", "твои файлы"],
        "typing": [
            "Одна память для всех ИИ",
            "Бесплатно, на твоём компьютере, без аккаунта",
        ],
        "lead": "Mnemai помнит, кто ты, над чем работаешь, что решил и как тебе отвечать, — и подставляет это в любой ИИ. Память — папка обычных Markdown-файлов на твоём компьютере. Без облака и без аккаунта.",
        "dl": ("Скачать для", "все файлы"),
        "hero_alt": "Вопрос, и ответ приходит из памяти: план недели таблицей, с ценой и правилом про встречи, которые Mnemai уже знает",
        "hero_cap": "Спрашиваешь «что главное на неделе?» — план приходит таблицей, с решённой ценой и твоим правилом про встречи. Повторять их не пришлось.",
        "langs": "Языки",
        "what": "Что умеет",
        "grid": [
            ("🧠", "Знает тебя", "Портрет, который ИИ читает первым, живая карта памяти, твои обычные файлы."),
            ("🗣️", "Консорциум", "Claude, ChatGPT и Gemini спорят и сходятся на одном ответе."),
            ("🎙️", "Встречи", "Созвон превращается в расшифровку, итоги и задачи с ответственными."),
            ("🔐", "Приватно", "Пароль на память, как в KeePass. Секреты не уходят в облако."),
            ("💻", "Без интернета", "13 бесплатных моделей прямо на компьютере, без ключей."),
            ("📉", "Меньше токенов", "Модели уходит только нужное: на длинном договоре в 4,8 раза меньше токенов."),
        ],
        "sec": [
            (
                "🧠 Она тебя знает",
                "memory",
                "Портрет и карта памяти: темы пузырями, размер — сколько Mnemai знает",
                [
                    "**Портрет, который каждый ИИ читает первым:** кто ты, что строишь, как с тобой работать. Mnemai пишет его сама, поправить можно руками.",
                    "**Карта памяти:** каждая тема — пузырь, пульсирует — недавно менялась, замок — её видят не все ИИ.",
                    "**Старое не выдаётся за новое:** у каждого факта дата, статус старше месяца Mnemai переспросит.",
                    "**Не одна папка:** подключи хранилище Obsidian или папку команды — только чтение, запись туда запрещена в самой программе.",
                ],
            ),
            (
                "🗣️ Консорциум: несколько ИИ, один ответ",
                "consortium",
                "Claude, ChatGPT и Gemini обсуждают вопрос, один подводит итог",
                [
                    "**Совет, дебаты, мозговой штурм, красная команда, прожарка** — выбираешь формат и число кругов.",
                    "**Вмешаться можно в любой момент:** «Остановить» прерывает текущий ИИ и сохраняет сказанное.",
                    "**Поспорить с разными ИИ** под любым ответом: автор защищает, остальные ищут, где он неправ.",
                ],
            ),
            (
                "🎙️ Встречи: от созвона к задачам",
                "meetings",
                "Как идёт встреча: запись, расшифровка, итоги, память — у каждого шага свои настройки",
                [
                    "**Две дорожки:** твой микрофон и звук компьютера, поэтому в расшифровке видно, кто говорит.",
                    "**Whisper на компьютере бесплатно** или облачный Whisper (≈ $0.36 за час) — тишину, выдуманные фразы и эхо Mnemai вырезает.",
                    "**Итоги:** что решили, какие задачи и за кем — любой моделью на выбор, в том числе на компьютере.",
                    "**Готовые настройки:** Приватно, Баланс, Быстро задают весь путь сразу.",
                ],
            ),
            (
                "🌱 Учится сама",
                "learning",
                "Ты говоришь что-то между делом, а в ленте видно, что Mnemai прочитала, поняла и записала, и почему",
                [
                    "**Уверена — записывает:** факт с уверенностью от 80% записывается сразу, сомнительный ждёт повтора.",
                    "**Личное — отдельно:** деньги, здоровье и личное попадают в помеченные карточки, их можно скрыть от любого ИИ.",
                    "**Ничего не прячет:** в ленте «Что я поняла и почему» видно каждое решение с причиной.",
                ],
            ),
            (
                "✈️ Читает Telegram, но ничего туда не пишет",
                "telegram",
                "Telegram подключён только на чтение: ты выбираешь чаты, Mnemai по ним учится",
                [
                    "**Чаты выбираешь ты:** Mnemai узнаёт тебя и людей вокруг только по ним.",
                    "**Только чтение, в самой программе:** клиент Telegram внутри Mnemai умеет только читать, любая другая команда отклоняется до отправки.",
                    "**Всё на твоём компьютере:** вход зашифрован в хранилище системы, своих серверов у Mnemai нет.",
                ],
            ),
            (
                "📉 Экономит токены",
                "tokens",
                "Вопрос по договору в 153 000 знаков: 29 643 входных токена на весь текст, 6 159 с Mnemai",
                [
                    "**Уходит только нужное:** память, документы и страницы читаются на компьютере, модели достаются нужные куски.",
                    "**Замер:** вопрос по договору в 153 000 знаков — весь текст занял 29 643 входных токена, Mnemai отправила 6 159, и правильный ответ дал только вариант с Mnemai.",
                    "**Видно каждый раз:** под каждым ответом написано, сколько токенов сэкономлено.",
                ],
                560,
            ),
        ],
        "priv": "🔐 Приватно по устройству",
        "priv_l": ("lock", "Первый запуск: пароль на память, как в KeePass"),
        "priv_r": ("privacy", "Кто что видит: галочка на часть памяти, замок на тему"),
        "priv_text": [
            "**Пароль на память:** AES-256, ключ получается из твоего пароля, шифрование открытое. Без него заметки не прочитать, даже скопировав их с диска. Копия при синхронизации тоже зашифрована.",
            "**Секреты остаются у тебя:** номера карт, пароли, ключи и телефоны заменяются метками до отправки в облачную модель.",
            "**У каждого ИИ свой доступ:** деньги, здоровье и личное скрываются от любого из них одним щелчком.",
        ],
        "works": "🤖 С чем работает",
        "works_note": "Подписку ChatGPT подключает официальное окно Sign in with ChatGPT с отдельным согласием на использование лимита плана; генерация работает через Codex App Server. OpenCode Go подключается ключом своей подписки.",
        "groups": [
            ("Облачные ИИ", "по ключу или подписке"),
            ("На компьютере", "бесплатно, без интернета"),
            ("В твоих программах", "через MCP"),
            ("Системы", "одна программа"),
        ],
        "local": "Встроенная",
        "more": "И ещё",
        "more_text": [
            "**Работает с файлами.** Читает сканы, пишет заметки, делает PDF, Word и Excel, склеивает и режет PDF. Любую запись можно откатить: Память → История.",
            "**Команды без модели.** «Открой википедию со словом „сон“», «открой в ютубе …», «открой гугл» и другие однозначные просьбы выполняются сразу, без обращения к ИИ — одинаково на любой модели.",
            "**Пароль администратора — в чате.** Для sudo и установки не нужно окно терминала: Mnemai спросит пароль прямо в разговоре, один раз, и он не попадёт ни в переписку, ни к модели.",
            "**Девять языков.** Интерфейс и ответы ИИ идут на выбранном, даже если пишешь на другом.",
        ],
        "fold": ["Установка", "Сборка из исходников", "Как устроено", "Безопасность"],
        "lic": "Лицензия",
        "foot": "Если Mnemai помнит для тебя что-то полезное, ⭐ поможет её найти другим.",
    },
}


PARTS = ["install", "build", "how", "security"]  # folded, in this order; then the license
# code, native name, flag, file, the word for «guide» in the table
LANGS = [
    ("en", "English", "gb", "README.md", "Guide"),
    ("ru", "Русский", "ru", "README.ru.md", "Справочник"),
    ("zh", "中文", "cn", "README.zh.md", "指南"),
    ("es", "Español", "es", "README.es.md", "Guía"),
    ("hi", "हिन्दी", "in", "README.hi.md", "गाइड"),
    ("pt", "Português", "pt", "README.pt.md", "Guia"),
    ("fr", "Français", "fr", "README.fr.md", "Guide"),
    ("de", "Deutsch", "de", "README.de.md", "Handbuch"),
    ("ja", "日本語", "jp", "README.ja.md", "ガイド"),
]
NAMES = {
    "zh": "Simplified Chinese",
    "es": "Spanish",
    "hi": "Hindi",
    "pt": "Portuguese (Brazil)",
    "fr": "French",
    "de": "German",
    "ja": "Japanese",
}


def strings(lang: str) -> dict:
    if lang in L:
        return L[lang]
    f = ROOT / "docs" / "readme" / lang / "strings.json"
    if not f.exists():
        raise SystemExit(f"{lang}: нет перевода — запусти с --translate")
    return {**json.loads(f.read_text(encoding="utf-8")), "file": dict((x[0], x[3]) for x in LANGS)[lang]}


def lang_table(lang: str) -> str:
    """Ten flags, two rows: each language with its README and its guide."""
    cells = []
    for code, native, flag, file, guide in LANGS:
        name = f"<b>{native}</b>" if code != lang else f"<b>✓ {native}</b>"
        cells.append(
            f'<td align="center" width="10%"><img src="https://flagcdn.com/w80/{flag}.png" width="36" alt="{native}"><br>{name}'
            f'<br><sub><a href="{file}">README</a> · <a href="docs/guide/{code}.md">{guide}</a></sub></td>'
        )
    return "<table>\n<tr>" + "".join(cells[:5]) + "</tr>\n<tr>" + "".join(cells[5:]) + "</tr>\n</table>\n"


def build(lang: str) -> str:
    c = strings(lang)
    img = f"docs/img/{lang}"
    src = ROOT / "docs" / "readme" / lang

    def part(slug: str) -> str:
        return (src / f"{slug}.md").read_text(encoding="utf-8").strip()

    folds = {s: part(s) for s in PARTS}
    lic = part("license")

    out = []
    out.append('<div align="center">\n')
    out.append('<img src="docs/img/brand/logo.svg" width="112" alt="Mnemai">\n')
    out.append("# Mnemai\n")
    out.append(f'<img src="{typing(c["typing"])}" alt="{c["typing"][0]}">\n')
    out.append(
        " ".join(
            [
                f'<a href="https://github.com/{REPO}/actions/workflows/tests.yml"><img src="https://img.shields.io/github/actions/workflow/status/{REPO}/tests.yml?branch=main&style=flat-square&label=tests" alt="tests"></a>',
                '<a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-0ea5e9?style=flat-square" alt="license"></a>',
                f'<a href="https://github.com/{REPO}/commits/main"><img src="https://img.shields.io/github/last-commit/{REPO}?style=flat-square&color=ec4899" alt="last commit"></a>',
            ]
        )
        + "\n"
    )
    ro, ro2, enc, files = c["badges"]
    out.append(
        " ".join(
            f'<img src="{badge(a, b, col, logo)}" alt="{a}: {b}">'
            for a, b, col, logo in [
                ("MCP", "Claude · Cursor", "7c3aed", "modelcontextprotocol"),
                ("Obsidian", ro, "7c3aed", "obsidian"),
                ("Telegram", ro2, "229ED9", "telegram"),
                ("AES-256", enc, "15803d", ""),
                ("Markdown", files, "555555", "markdown"),
                ("Python", "3.13", "3776ab", "python"),
            ]
        )
        + "\n"
    )
    out.append(
        f'<a href="docs/guide/{lang}.md"><img src="{badge(c["guide_btn"], c["guide_msg"], "8b5cf6", "gitbook", "for-the-badge")}" alt="{c["guide_btn"]}"></a>\n'
    )
    # the code to the repository: for a screen at a conference (docs/img/brand/qr.svg, tools/qr_build.py)
    out.append(
        f'<a href="https://github.com/{REPO}"><img src="docs/img/brand/qr.svg" width="220" alt="QR: github.com/{REPO}"></a>'
        f"<br><sub>{c['qr']} · github.com/{REPO}</sub>\n"
    )
    out.append("</div>\n")
    out.append(f"## {c['langs']}\n\n{c['langs_intro']}\n\n{lang_table(lang)}")
    out.append('<div align="center">\n')
    out.append(f"{c['lead']}\n")
    dl, alltxt = c["dl"]
    out.append(
        " ".join(
            [
                f'<a href="../../releases/latest/download/Mnemai-Setup.exe"><img src="{badge(dl, "Windows", "0078D4", "", "for-the-badge")}" alt="Windows"></a>',
                f'<a href="../../releases/latest/download/Mnemai-macos-arm64.dmg"><img src="{badge(dl, "macOS", "111111", "apple", "for-the-badge")}" alt="macOS"></a>',
                f'<a href="../../releases/latest/download/Mnemai-x86_64.AppImage"><img src="{badge(dl, "Linux", "E95420", "linux", "for-the-badge")}" alt="Linux"></a>',
            ]
        )
        + f'\n\n<sub><a href="../../releases">{alltxt}</a> · macOS Intel: <a href="../../releases/latest/download/Mnemai-macos-x64.dmg">x64.dmg</a></sub>\n'
    )
    out.append(f'<img src="{img}/hero.gif" width="880" alt="{c["hero_alt"]}">\n')
    out.append(f"<sub>{c['hero_cap']}</sub>\n")
    out.append("</div>\n")

    rows = [c["grid"][i : i + 3] for i in range(0, 6, 3)]
    grid = (
        "<table>\n"
        + "".join(
            "<tr>\n" + "".join(f'<td width="33%" valign="top"><h3>{e} {t}</h3>{d}</td>\n' for e, t, d in r) + "</tr>\n"
            for r in rows
        )
        + "</table>\n"
    )
    out.append(f"## ✨ {c['what']}\n\n{grid}")

    for title, gif, alt, bullets, *rest in c["sec"]:
        out.append(f"## {title}\n")
        out.append(
            f'<p align="center"><img src="{img}/{gif}.gif" width="{rest[0] if rest else 860}" alt="{alt}"></p>\n'
        )
        out.append("\n".join(f"- {b}" for b in bullets) + "\n")

    out.append(f"## {c['priv']}\n")
    (lg, la), (rg, ra) = c["priv_l"], c["priv_r"]
    out.append(
        f'<table><tr><td width="50%" valign="top" align="center"><img src="{img}/{lg}.gif" alt="{la}"><br><sub>{la}</sub></td>'
        f'<td width="50%" valign="top" align="center"><img src="{img}/{rg}.gif" alt="{ra}"><br><sub>{ra}</sub></td></tr></table>\n'
    )
    out.append("\n".join(f"- {b}" for b in c["priv_text"]) + "\n")

    g = c["groups"]
    cloud = "".join(
        tile(n, n2, f"docs/img/brand/{n}.svg")
        for n, n2 in [
            ("claude", "Claude"),
            ("chatgpt", "ChatGPT"),
            ("gemini", "Gemini"),
            ("deepseek", "DeepSeek"),
            ("yandex", "YandexGPT"),
            ("openrouter", "OpenRouter"),
        ]
    )
    local = (
        tile("local", c["local"], "docs/img/brand/local.svg")
        + tile("ollama", "Ollama", f"{SI}/ollama/ffffff")
        + tile("strata", "Strata", "docs/img/brand/strata.svg")
    )
    tools = tile("claude", "Claude Code", f"{SI}/claude/D97757") + tile("cursor", "Cursor", "docs/img/brand/cursor.svg")
    systems = (
        tile("windows", "Windows", "docs/img/brand/windows.svg")
        + tile("apple", "macOS", f"{SI}/apple/ffffff")
        + tile("linux", "Linux", f"{SI}/linux/FCC624")
    )

    # one grid, a row per group: the group on the left, its AIs across — never wider than the page
    rows = [(0, cloud), (1, local), (2, tools), (3, systems)]
    width = max(cells.count("<td") for _, cells in rows)

    def row(i, cells):
        pad = "<td></td>" * (width - cells.count("<td"))
        return f'<tr><td valign="middle" width="150"><b>{g[i][0]}</b><br><sub>{g[i][1]}</sub></td>{cells}{pad}</tr>'

    out.append(f"## {c['works']}\n")
    note = f"<p>{c['works_note']}</p>\n" if c.get("works_note") else ""
    out.append(
        '<div align="center">\n<table>' + "".join(row(i, cells) for i, cells in rows) + "</table>\n" + note + "</div>\n"
    )

    out.append(f"## ⚡ {c['more']}\n")
    out.append("\n".join(f"- {b}" for b in c["more_text"]) + "\n")

    for s, title in zip(PARTS, c["fold"]):
        out.append(f"<details>\n<summary><b>{title}</b></summary>\n\n{folds[s]}\n\n</details>\n")

    out.append(f"## {c['lic']}\n\n{lic}\n")
    out.append(
        f'<div align="center">\n<img src="docs/img/brand/logo.svg" width="40" alt="Mnemai">\n\n<sub>{c["foot"]}</sub>\n</div>\n'
    )
    text = "\n".join(out)
    return text


# ---------------------------------------------------------------- translating the other eight, once

PROMPT_STRINGS = """You translate the texts of the GitHub README of Mnemai — a free desktop app that keeps a person's memory
for every AI (Claude, ChatGPT, Gemini, local models) as Markdown files on their own computer — into {lang}.

Below is a JSON object in English. Return ONLY a JSON object with exactly the same structure: the same keys, the same
list lengths, the same order. Translate every human-readable text. Keep unchanged: emoji, numbers, Markdown (**bold**),
«quotes» style adapted to {lang}, the animation ids (memory, consortium, meetings, learning, telegram, tokens, lock,
privacy) and any number that is a width. Keep brand and product names (Mnemai, Claude, Claude Code, ChatGPT, Gemini,
OpenRouter, Ollama, Cursor, Obsidian, Markdown, Telegram, Whisper, KeePass, AES-256, MCP, API, PDF, Word, Excel,
QuickBooks, Windows, macOS, Linux). The «typing» lines are short slogans: keep them short (under 40 characters).
Address the reader informally where the language allows it, like a friendly modern app.

JSON:
{items}"""

PROMPT_PART = """Translate this part of the GitHub README of Mnemai (a desktop app that keeps memory for every AI) from
English into {lang}. Return ONLY the translated Markdown. Keep the Markdown structure, tables, links, code blocks
and commands exactly; do not translate code, commands, file names, paths, URLs, product names.

{text}"""


def ask(prompt: str) -> str:
    sys.path.insert(0, str(ROOT))
    from mnema import net
    from mnema.chat.providers import claude_exe

    p = subprocess.run(
        [
            claude_exe(),
            "-p",
            "--model",
            "sonnet",
            "--output-format",
            "text",
            "--tools",
            "",
            "--setting-sources",
            "",
            "--strict-mcp-config",
            "--no-session-persistence",
        ],
        input=prompt.encode("utf-8"),
        capture_output=True,
        cwd=Path(tempfile.gettempdir()),
        env=net.env(),
        timeout=900,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return p.stdout.decode("utf-8", "replace").strip()


def same_shape(a, b) -> bool:
    if isinstance(a, dict):
        return isinstance(b, dict) and a.keys() == b.keys() and all(same_shape(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)):
        return isinstance(b, list) and len(a) == len(b) and all(same_shape(x, y) for x, y in zip(a, b))
    if isinstance(a, int):
        return a == b
    return isinstance(b, str)


def translate(lang: str) -> None:
    d = ROOT / "docs" / "readme" / lang
    d.mkdir(parents=True, exist_ok=True)
    name = NAMES[lang]
    f = d / "strings.json"
    if not f.exists():
        en = {k: v for k, v in L["en"].items() if k != "file"}
        en = json.loads(json.dumps(en))  # tuples → lists
        for _ in range(3):
            m = re.search(
                r"\{.*\}", ask(PROMPT_STRINGS.format(lang=name, items=json.dumps(en, ensure_ascii=False))), re.S
            )
            try:
                got = json.loads(m.group(0)) if m else None
            except ValueError:
                got = None
            if got and same_shape(en, got) and all(x[1] == y[1] for x, y in zip(en["sec"], got["sec"])):
                f.write_text(json.dumps(got, ensure_ascii=False, indent=1), encoding="utf-8")
                break
        else:
            print(f"{lang}: строки не перевелись", flush=True)
    for slug in PARTS + ["license"]:
        pf = d / f"{slug}.md"
        if pf.exists():
            continue
        text = (ROOT / "docs" / "readme" / "en" / f"{slug}.md").read_text(encoding="utf-8")
        out = re.sub(r"^```(?:markdown)?\s*\n(?=[^`])|\n```\s*$", "", ask(PROMPT_PART.format(lang=name, text=text)))
        if len(out) > len(text) * 0.15:  # Chinese and Japanese are much shorter than English
            pf.write_text(out.strip() + "\n", encoding="utf-8")
        else:
            print(f"{lang}/{slug}: не перевелось", flush=True)
    print(f"{lang}: ready", flush=True)


if __name__ == "__main__":
    if "--translate" in sys.argv:
        with cf.ThreadPoolExecutor(4) as ex:
            list(ex.map(translate, NAMES))
    for code, *_ in LANGS:
        text = build(code)
        (ROOT / dict((x[0], x[3]) for x in LANGS)[code]).write_text(text, encoding="utf-8")
        print(dict((x[0], x[3]) for x in LANGS)[code], len(text))
