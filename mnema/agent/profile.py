"""Behavior profile: every fine point of how an AI should work with a person, as sections of toggles.

The catalog is a short set of common rules: how to talk, how to take a task, facts, memory, privacy, layout.
Each item is a rule the system prompt carries when it's on. Presets switch many toggles at once. Packs export/import the settings.

Stored in <vault>/.mnema/agent.json.
"""

from __future__ import annotations

from copy import deepcopy

from ..vault import Vault
from ..fsutil import read_json, write_json

# (id, title shown in settings, rule for the model, default)
CATALOG: list[dict] = [
    {
        "id": "talk",
        "title": "Как говорить",
        "items": [
            ("ty", "Обращаться на ты", "Обращайся на ты.", True),
            ("no_filler", "По существу", "Отвечай по существу, без вступлений и повторов.", True),
            ("lead", "Сначала главное", "Начинай с главного, подробности — после.", True),
            ("plain", "Понятный язык", "Пиши понятным языком, термины поясняй.", True),
            (
                "no_stamps",
                "Без шаблонных фраз",
                "Не используй шаблонные фразы вроде «Отличный вопрос!» или «Надеюсь, это поможет».",
                True,
            ),
            ("humor", "Юмор к месту", "Шути редко и только к месту.", True),
        ],
    },
    {
        "id": "task",
        "title": "Работа с задачей",
        "items": [
            ("only_asked", "Только то, что просили", "Делай то, о чём просили, без лишнего.", True),
            (
                "ask_options",
                "Вопросы — вариантами",
                "Уточняющий вопрос задавай с вариантами ответа (кнопками), а не списком вопросов в тексте.",
                True,
            ),
            (
                "ask_hints",
                "Пояснять варианты",
                "К уточняющему вопросу добавляй одной фразой, зачем спрашиваешь, а к каждому варианту — что будет, "
                "если выбрать его.",
                True,
            ),
        ],
    },
    {
        "id": "facts",
        "title": "Факты",
        "items": [
            ("no_invent", "Без выдумок", "Ничего не выдумывай: если не знаешь — так и скажи.", True),
            (
                "memory_first",
                "Опираться на память",
                "Утверждая что-то о человеке, опирайся на память, а не на догадку.",
                True,
            ),
            ("second_pass", "Перечитывать ответ перед отправкой", "", False),
        ],
    },
    {
        "id": "memory",
        "title": "Память",
        "items": [
            (
                "say_saved",
                "Говорить о новом",
                "Если узнал о человеке что-то важное, коротко скажи об этом в конце ответа.",
                False,
            ),
        ],
    },
    {
        "id": "privacy",
        "title": "Приватность",
        "items": [
            (
                "no_secrets",
                "Секреты не повторять",
                "Не повторяй в ответах пароли, ключи и номера документов, даже если они встретились.",
                True,
            ),
        ],
    },
    {
        "id": "docs",
        "title": "Оформление",
        "items": [
            ("tables", "Сравнения — таблицей", "Сравнения и данные с параметрами оформляй таблицей.", True),
        ],
    },
]

PRESETS = {
    "soft": {
        "name": "Мягкий",
        "note": "Дружелюбный собеседник: меньше правил.",
        "off": ["only_asked", "ask_hints", "tables", "lead"],
    },
    "business": {
        "name": "Деловой",
        "note": "Коротко, по делу, без выдумок.",
        "off": ["second_pass"],
    },
    "strict": {
        "name": "Строгий с проверками",
        "note": "Все правила и проверка ответа перед отправкой.",
        "on_all": True,
    },
}

SIMPLE = {
    "address": {"title": "Обращение", "choices": {"ty": "на ты", "vy": "на вы"}, "default": "ty"},
    "length": {
        "title": "Длина ответов",
        "choices": {"short": "коротко", "normal": "по делу", "long": "подробно"},
        "default": "normal",
    },
    "autonomy": {
        "title": "Насколько сама учится",
        "choices": {
            "observe": "только смотрит",
            "approve": "всё спрашивает",
            "mixed": "уверенное сама",
            "quiet": "всё сама",
        },
        "default": "mixed",
    },
}

DEFAULT = {
    # Mnemai as memory: on — AIs get the owner's memory and Mnemai learns; off — plain chat, nothing is given or written.
    # A memory folder made on the first screen starts with it off (the tour offers to turn it on); folders that
    # existed before the switch keep memory on.
    "memory_on": True,
    "memory_asked": False,  # the owner answered «Включить память?» (the tour or the question on its own)
    "preset": "business",
    "toggles": {},  # id → bool, overrides catalog default
    "simple": {k: v["default"] for k, v in SIMPLE.items()},
    "custom": "",  # free text added to the instructions
    "default_model": "",  # "provider:model"
    "team_vault": "",  # before 1.4: one shared folder; read as the first of extra_folders
    "extra_folders": [],  # more folders the memory reaches into (notes, an Obsidian vault, another Mnemai memory)
    "tg_read": {},  # reading the owner's chats through the Telegram API (learn/tg_api.py): api_id, phone, who logged in
    "self_ask": True,  # a question of her own now and then when the talk is about a project (chat/selfask.py)
    "self_ask_next": "",  # not before this time: 40–120 minutes after the last such question
    "local_offer": "",  # first-launch offer of the built-in model: "" → show, "dismissed" / "done"
    "scribe_model": "auto",  # meeting scribe: auto (medium if downloaded) | small | medium | large-v3
    "proxy": "",  # "" — the Windows system proxy, "off" — direct, or http://host:port
    "economy": True,  # token economy: memory, documents and history trimmed to the question on the computer
    "web": False,  # «Интернет» switch in the composer: search the web for every message
    "terms": True,  # «Подсказки»: the model adds a glossary, the chat shows it as pop-up hints
    "tools": True,  # «Действия на компьютере»: the model may read and write files and run terminal commands
    "pc_access": True,  # the terminal and PC control are allowed by default; off — files only
    "tool_folders": [],  # work folders open for actions besides the memory folder
    "tools_ask": False,  # ask the owner before each action; off — actions run at once, undo stays in «История»
    "ui_theme": "",  # chosen on the first screen: light | dark | system; the app starts in it
    "vpn_key_on": False,  # connected by a VPN key (vpnkey.py); the key itself is in the Windows secret store
    "vpn_service": "",  # which app the key came from (Hiddify, Happ, …) — only for the hint
    "vpn_name": "",  # the server name from the key
    "vpn_error": "",  # the last check of the VPN failed: what the owner sees instead of «VPN включён»
    "last_model": "",  # the model the owner picked last — the app starts with it
    "lang": "en",  # interface language and the language of answers
    "gender": "",  # the owner: "m" | "f" | "" — for grammar when the AI addresses them
    "owner_name": "",  # how to call the owner
    "prompts_mode": "second",  # prompts for recurring tasks: off | second (the second similar request) | every
    "prompts_auto": True,  # use a saved prompt when a request matches it
    "prompts_never": [],  # requests the owner said "don't offer for these" about (term signatures)
    "scribe_keep_audio": False,
    "scribe_summary_model": "",  # meetings: which model sums up ("" — the chat's model)        # meetings: keep the audio after transcription (the transcript is always kept)
    "scribe_mode": "auto",  # meetings: auto (by this computer's speed) | local | partial | cloud
    "scribe_base": "",  # own OpenAI-compatible address for the cloud Whisper ("" — the OpenAI key)
    "scribe_cloud_model": "",
    "scribe_rtf": 0,  # last measured: seconds of work per second of audio on this computer
    "sync": {},  # free sync as open files: targets (gdrive, dropbox, folder, station) and minutes
    "redact": True,  # swap card numbers, passwords, keys, phones for labels before a cloud AI sees them
    "engine": {},  # tokens and computer load: mode eco|balance|max|custom + sliders (see tuning.py)
}


def _file(vault: Vault):
    return vault.service / "agent.json"


def defaults() -> dict[str, bool]:
    return {i[0]: i[3] for sec in CATALOG for i in sec["items"]}


def memory_on(vault: Vault) -> bool:
    try:
        return bool(load(vault).get("memory_on", True))
    except Exception:
        return True


MEMORY_OFF = "Память Mnemai выключена: ИИ ничего о тебе не знают, и ничего не запоминается. Включить — Настройки → Обучение → «Память»."


def load(vault: Vault) -> dict:
    f = _file(vault)
    data = read_json(f, {}) or {}
    out = deepcopy(DEFAULT)
    for k, v in data.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k].update(v)
        else:
            out[k] = v
    return out


def save(vault: Vault, prof: dict) -> dict:
    cur = load(vault)
    for k, v in prof.items():
        if k in DEFAULT:
            if isinstance(v, dict) and isinstance(cur.get(k), dict):
                cur[k].update(v)
            else:
                cur[k] = v
    vault.service.mkdir(parents=True, exist_ok=True)
    write_json(_file(vault), cur, indent=2)
    return cur


def effective(prof: dict) -> dict[str, bool]:
    """Catalog defaults ← preset ← the owner's own toggles."""
    eff = defaults()
    p = PRESETS.get(prof.get("preset") or "", {})
    if p.get("on_all"):
        eff = {k: True for k in eff}
    for k in p.get("off", []):
        eff[k] = False
    for k, v in (prof.get("toggles") or {}).items():
        if k in eff:
            eff[k] = bool(v)
    return eff


def apply_preset(vault: Vault, preset: str) -> dict:
    if preset not in PRESETS:
        raise ValueError("нет такого набора")
    return save(vault, {"preset": preset, "toggles": {}})


def catalog_view(prof: dict) -> list[dict]:
    eff = effective(prof)
    return [
        {
            "id": s["id"],
            "title": s["title"],
            "items": [
                {
                    "id": i[0],
                    "title": i[1],
                    "rule": i[2]
                    or "После черновика модель проверяет ответ по включённым правилам и исправляет его. Дольше и дороже.",
                    "on": eff[i[0]],
                }
                for i in s["items"]
            ],
        }
        for s in CATALOG
    ]


def rules_text(prof: dict) -> str:
    """The behavior part of the system prompt."""
    eff = effective(prof)
    simple = prof.get("simple") or {}
    lines = []
    for s in CATALOG:
        sec = [i[2] for i in s["items"] if eff[i[0]] and i[2]]
        if s["id"] == "talk":
            sec = [r for r in sec if not r.startswith("Обращайся на ты")]
            sec.insert(0, "Обращайся на ты." if simple.get("address", "ty") == "ty" else "Обращайся на вы.")
            who = []
            if (prof.get("owner_name") or "").strip():
                who.append(f"Владельца зовут {prof['owner_name'].strip()}, так к нему и обращайся.")
            if prof.get("gender") in ("m", "f"):
                who.append(
                    "Владелец — "
                    + (
                        "мужчина: в обращении мужской род."
                        if prof["gender"] == "m"
                        else "женщина: в обращении женский род."
                    )
                )
            sec[1:1] = who
            sec.insert(
                1,
                {
                    "short": "Отвечай как можно короче.",
                    "normal": "",
                    "long": "Отвечай развёрнуто, но вывод первым.",
                }.get(simple.get("length", "normal"), ""),
            )
            sec = [r for r in sec if r]
        if sec:
            lines.append(f"{s['title']}:\n" + "\n".join(f"- {r}" for r in sec))
    return "\n\n".join(lines)


# ---------------------------------------------------------------- packs (share settings without personal data)


def export_pack(prof: dict, name: str = "Мой набор") -> dict:
    return {
        "mnema_pack": 1,
        "name": name,
        "preset": prof.get("preset"),
        "toggles": prof.get("toggles") or {},
        "simple": {k: v for k, v in (prof.get("simple") or {}).items() if k in ("address", "length")},
    }


def import_pack(vault: Vault, pack: dict) -> dict:
    if not isinstance(pack, dict) or pack.get("mnema_pack") != 1:
        raise ValueError("это не набор Mnemai")
    known = defaults()
    return save(
        vault,
        {
            "preset": pack.get("preset") if pack.get("preset") in PRESETS else "business",
            "toggles": {k: bool(v) for k, v in (pack.get("toggles") or {}).items() if k in known},
            "simple": {
                k: v for k, v in (pack.get("simple") or {}).items() if k in SIMPLE and v in SIMPLE[k]["choices"]
            },
        },
    )
