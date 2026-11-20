"""Первые экраны окна (setup и missing): сборка страниц из статических файлов ui/.

Разметка и скрипты самих страниц лежат в ui/setup.html и ui/missing.html; в этом модуле — только тексты
переводов и подстановки (i18n-словарь, русские замены, путь папки), как было раньше. Поведение 1:1.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import osapi as OS

UI = Path(__file__).resolve().parent / "ui"

SETUP_RU = {  # the first two screens are in English for everyone, but in Russian on a Russian Windows
    "<h1>Light or dark?</h1>": "<h1>Светлая или тёмная?</h1>",
    "Pick how Mnemai looks. You can change it any time.": "Выбери, как будет выглядеть Mnemai. Поменять можно в любой момент.",
    "</svg>Light</b>": "</svg>Светлая</b>",
    "</svg>Dark</b>": "</svg>Тёмная</b>",
    "</svg>Like Windows</b>": "</svg>Как в Windows</b>",
    "Click a card to see how it looks.": "Нажми на карточку — покажу, как это будет выглядеть.",
    '<button id="n0">Continue</button>': '<button id="n0">Дальше</button>',
    "<h1>Choose your language</h1>": "<h1>Выбери язык</h1>",
    "Mnemai will speak with you in this language.": "На этом языке Mnemai будет говорить с тобой.",
    '<button class="l" id="b1">Back</button>': '<button class="l" id="b1">Назад</button>',
    '<button id="n1" disabled>Continue</button>': '<button id="n1" disabled>Дальше</button>',
    "'Follows Windows: light by day, dark at night if Windows does so.'": "'Как в Windows: днём светлая, ночью тёмная, если так настроена Windows.'",
    "'This is how it will look. Try another or continue.'": "'Так это будет выглядеть. Попробуй другую или жми «Дальше».'",
}

MISSING_TEXT = {
    "ru": (
        "Не нашла папку памяти",
        "Память была здесь:",
        "Если ты перенёс или переименовал папку, укажи, где она сейчас. Если это внешний диск — подключи его и "
        "нажми «Проверить снова». Ничего не удалено: Mnemai не трогала папку.",
        "Указать, где она",
        "Проверить снова",
        "Начать новую память",
    ),
    "en": (
        "Your memory folder is missing",
        "It used to be here:",
        "If you moved or renamed the folder, show where it is now. If it is on an external drive, plug it in and "
        "press «Check again». Nothing was deleted: Mnemai did not touch the folder.",
        "Show where it is",
        "Check again",
        "Start new memory",
    ),
}


def setup_source() -> str:
    return (UI / "setup.html").read_text(encoding="utf-8")


def setup_html(lang: str | None = None) -> str:
    """The first screen with its own texts translated into every language (from ui/i18n/*.json)."""
    html = setup_source()
    texts = set(t.strip() for t in re.findall(r">([^<>]*[А-Яа-яЁё][^<>]*)<", html))
    texts |= set(re.findall(r'placeholder="([^"]*[А-Яа-яЁё][^"]*)"', html))
    texts |= set(re.findall(r"T\('([^']+)'\)", html))
    d = {}
    folder = UI / "i18n"
    for f in folder.glob("*.json") if folder.exists() else []:
        try:
            exact = json.loads(f.read_text(encoding="utf-8")).get("exact", {})
        except ValueError:
            continue
        d[f.stem] = {t: exact[t] for t in texts if t in exact}
    html = html.replace("__SETUP_I18N__", json.dumps(d, ensure_ascii=False))
    if lang == "ru":  # English by default; Russian only when asked for
        for en, ru in SETUP_RU.items():
            html = html.replace(en, ru)
    return OS.os_words(html)


def missing_html(path: str, lang: str = "ru") -> str:
    """The memory folder from the last run is gone (moved, renamed, a drive not plugged in): say so, never start over
    silently."""
    import html as _h

    t = MISSING_TEXT["ru" if (lang or "ru") == "ru" else "en"]
    page = (UI / "missing.html").read_text(encoding="utf-8").rstrip("\n")  # байт-в-байт со старой страницей
    return (
        page.replace("__LANG__", "ru" if lang == "ru" else "en")
        .replace("__PATH__", _h.escape(path))
        .replace("__T0__", _h.escape(t[0]))
        .replace("__T1__", _h.escape(t[1]))
        .replace("__T2__", _h.escape(t[2]))
        .replace("__T3__", _h.escape(t[3]))
        .replace("__T4__", _h.escape(t[4]))
        .replace("__T5__", _h.escape(t[5]))
    )
