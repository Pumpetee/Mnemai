"""Short computer commands answered without asking a model.

«Открой терминал», «прочитай файл ~/план.md», «что в папке ~/Загрузки», «найди договор в файлах»,
«выполни echo ok», «запомни: …», «который час» are one action and one short line, not a conversation. Doing them
through a 40–90 s model call (and a second call to retell the result) is why a simple request felt like a hang.
The same deterministic path works for every model; unrecognised talk still goes to the model.
"""

from __future__ import annotations

import datetime as dt
import re
import shutil
from pathlib import Path

from ..vault import Vault
from . import tools as TL

OPEN = re.compile(
    r"^\s*(?:пожалуйста[,\s]+)?(?:открой(?:те)?|запусти(?:те)?|открывай(?:те)?|open|launch)\s+(?:мне\s+)?(.+?)\s*[.!?]*$",
    re.I,
)
READ = re.compile(r"^\s*(?:прочитай|прочти|покажи содержимое|покажи файл|что в файле)\s+(?:файл\s+)?(.+?)\s*[.!?]*$", re.I)
LIST = re.compile(r"^\s*(?:что\s+(?:в|лежит в)\s+(?:папке\s+)?|покажи папку|список файлов(?: в)?)\s*(.+?)\s*[.!?]*$", re.I)
FIND = re.compile(r"^\s*(?:найди|поищи)\s+(.+?)\s+(?:в файлах|по файлам|в документах)\s*[.!?]*$", re.I)
COMMAND = re.compile(
    r"^\s*(?:(?:выполни|выполнить|команда|запусти(?:те)?\s+(?:в\s+терминале\s+)?(?:команду\s+)?)\s*[:：]?\s*|"
    r"!(?:bash|sh)?\s*|/run\s+)(.+)$",
    re.I | re.S,
)
REMEMBER = re.compile(r"^\s*(?:запомни(?:,\s*что)?|запиши в память)\s*[:：]?\s*(.+)$", re.I | re.S)
WRITE = re.compile(
    r"^\s*(?:создай|создать|запиши|записать|сохрани|сохранить)\s+(?:мне\s+)?файл\s+(.+?)\s+"
    r"с\s+(?:текстом|содержимым)\s*[:：]\s*(.+)$",
    re.I | re.S,
)
DOC = re.compile(
    r"^\s*(?:сделай|создай|сгенерируй)\s+(pdf|pdf-файл|word|docx|excel|xlsx|документ)\s+(.+?)\s+"
    r"из\s*[:：]\s*(.+)$",
    re.I | re.S,
)
MEMFIND = re.compile(r"^\s*(?:найди|поищи|что\s+(?:есть|записано))\s+(.+?)\s+(?:в памяти|по памяти)\s*[.!?]*$", re.I)
SHOWMEM = re.compile(
    r"^\s*(?:что\s+(?:у тебя\s+)?в памяти|покажи память|что записано в памяти|"
    r"что ты (?:обо мне\s+)?знаешь|что ты знаешь обо мне|что ты помнишь обо мне)\s*[?.!]*$",
    re.I,
)
POLITE = re.compile(r"[,\s]*(?:пожалуйста|плиз|please)[.!?]*$", re.I)

# Names the owner may say besides the executable names the action already knows.
NAMES = {
    "терминал": "terminal",
    "терминала": "terminal",
    "консоль": "terminal",
    "консолька": "terminal",
    "terminal": "terminal",
    "console": "terminal",
    "konsole": "terminal",
    "хром": "chrome",
    "chrome": "chrome",
    "гугл хром": "chrome",
    "google chrome": "chrome",
    "браузер chrome": "chrome",
    "файрфокс": "firefox",
    "firefox": "firefox",
    "мозила": "firefox",
    "телеграм": "telegram",
    "телеграмм": "telegram",
    "telegram": "telegram",
    "код": "code",
    "vscode": "code",
    "vs code": "code",
    "файловый менеджер": "dolphin",
    "проводник": "dolphin",
    "dolphin": "dolphin",
}

FOLDERS = {
    "загрузки": "~/Загрузки",
    "загрузках": "~/Загрузки",
    "документы": "~/Документы",
    "документах": "~/Документы",
    "рабочий стол": "~/Рабочий стол",
    "стол": "~/Рабочий стол",
    "изображения": "~/Изображения",
    "картинки": "~/Изображения",
    "память": None,  # the vault root, filled at runtime
}


def _path(vault: Vault, raw: str) -> str:
    raw = " ".join(raw.strip().strip("«»\"'").split())
    low = raw.lower()
    if low in FOLDERS:
        raw = FOLDERS[low] or str(vault.root)
    p = Path(raw).expanduser()
    if not p.is_absolute():
        a, b = vault.root / p, Path.home() / p
        p = a if a.exists() else b if b.exists() else a
    return str(p)


def _target(text: str) -> str:
    return POLITE.sub("", text).strip().strip(" «»\"'").strip()


def fast_action(vault: Vault, text: str) -> dict | None:
    """The action to do right now, or None if this is ordinary talk (then the model answers)."""
    raw = (text or "").strip()
    if not raw:
        return None

    m = OPEN.match(raw)
    if m:
        target = _target(m.group(1))
        low = target.lower()
        for prefix in ("файл ", "файла ", "папку ", "папка ", "программу ", "программа ", "ссылку ", "ссылку на "):
            if low.startswith(prefix):
                target, low = _target(target[len(prefix):]), low[len(prefix):]
                break
        if low.startswith(("http://", "https://")):
            return {"tool": "open_app", "name": target, "label": "ссылка"}
        if low.startswith("www."):
            return {"tool": "open_app", "name": "https://" + target, "label": "ссылка"}
        if low in NAMES:
            return {"tool": "open_app", "name": NAMES[low], "label": NAMES[low]}
        if low in TL.APP_ALIASES:
            return {"tool": "open_app", "name": low, "label": low}
        path = _path(vault, target)
        if Path(path).exists():
            return {"tool": "open_app", "name": path, "label": "файл"}

    m = READ.match(raw)
    if m:
        path = _path(vault, _target(m.group(1)))
        return {"tool": "read_file", "path": path, "label": "файл"}
    m = LIST.match(raw)
    if m:
        path = _path(vault, _target(m.group(1)))
        return {"tool": "list_files", "path": path, "label": "папка"}
    m = FIND.match(raw)
    if m:
        return {"tool": "find_files", "query": _target(m.group(1)), "label": "поиск"}
    m = REMEMBER.match(raw)
    if m:
        fact = " ".join(m.group(1).split())[:400]
        return {"tool": "remember", "body": fact, "where": "inbox", "label": "память"} if len(fact) >= 6 else None
    m = WRITE.match(raw)
    if m:
        path = _path(vault, _target(m.group(1)))
        return {"tool": "write_file", "path": path, "body": m.group(2).strip(), "label": "файл"}
    m = DOC.match(raw)
    if m:
        kind = m.group(1).lower()
        path = _path(vault, _target(m.group(2)))
        ext = {"pdf": ".pdf", "pdf-файл": ".pdf", "word": ".docx", "docx": ".docx", "excel": ".xlsx", "xlsx": ".xlsx"}.get(kind)
        if ext and not path.lower().endswith(ext):
            path += ext
        return {"tool": "make_document", "path": path, "body": m.group(3).strip(), "label": "документ"}
    m = MEMFIND.match(raw)
    if m:
        return {"tool": "memory_find", "query": _target(m.group(1)), "label": "память"}
    if SHOWMEM.match(raw):
        return {"tool": "memory_show", "label": "память"}
    m = COMMAND.match(raw)
    if m and (raw.startswith(("!", "/run")) or re.match(r"^\s*(?:выполни|выполнить|команда|запусти)", raw, re.I)):
        command = m.group(1).strip()
        if command:
            return {"tool": "run_command", "command": command, "label": "команда"}
    if re.match(r"^\s*(?:который час|сколько времени|какое сегодня число|какая сегодня дата|дата и время)\s*[?.!]*$", raw, re.I):
        return {"tool": "time", "label": "время"}
    if re.match(r"^\s*(?:сколько (?:у меня )?(?:памяти|озу|ram|cpu|ядер|процессоров|места на диске)|какой у меня (?:процессор|компьютер)|система|о компьютере)\s*[?.!]*$", raw, re.I):
        return {"tool": "system", "label": "система"}
    return None


def _run(vault: Vault, tool: str, args: dict) -> tuple[str, str]:
    """(what the owner sees, the model-facing line)."""
    from ..memory import PermissionDenied, remember

    if tool == "remember":
        if not _memory_on(vault):
            return "Память выключена — не запоминаю.", ""
        try:
            remember(vault, args["body"], args.get("where", "inbox"), "owner")
        except (PermissionDenied, ValueError) as e:
            return f"Не запомнила: {e}", ""
        return "Запомнила.", ""
    if tool == "time":
        now = dt.datetime.now()
        months = "января февраля марта апреля мая июня июля августа сентября октября ноября декабря".split()
        return now.strftime("%H:%M, ") + f"{now.day} {months[now.month - 1]} {now.year}", ""
    if tool == "system":
        commands = (("ram", "free -h"), ("cpu", "nproc"), ("disk", "df -h / | tail -1"))
        parts = []
        for name, cmd in commands:
            try:
                result = TL.run(vault, {"tool": "run_command", "command": cmd, "timeout": 10}, "owner")[0]
            except Exception:
                continue
            body = result.split("\n", 1)[1] if "\n" in result else result
            if name == "cpu":
                body = f"Ядер CPU: {body.strip()}"
            elif name == "disk":
                body = "Диск: " + " ".join(body.split()[:5])
            else:
                body = body.strip().splitlines()[0] if body.strip() else ""
            parts.append(body)
        return "\n".join(p for p in parts if p) or "Не смогла узнать.", ""
    if tool == "memory_show":
        if not _memory_on(vault):
            return "Память выключена.", ""
        text = (vault.read_raw("10 Now.md") or "").strip() or "Память пуста."
        return text[:1200] + ("\n…[обрезано]" if len(text) > 1200 else ""), ""
    if tool == "memory_find":
        if not _memory_on(vault):
            return "Память выключена.", ""
        hits = vault.search(args["query"])
        if not hits:
            return "В памяти ничего не нашла.", ""
        return "\n".join(f"{rel}: {line.strip()}" for rel, line in hits[:12])[:1200], ""
    if tool == "write_file":
        _, line, _ = TL.run(vault, {"tool": "write_file", "path": args["path"], "body": args.get("body", "")}, "owner")
        return line + ".", ""
    if tool == "make_document":
        _, line, _ = TL.run(
            vault, {"tool": "make_document", "path": args["path"], "body": args.get("body", "")}, "owner"
        )
        return line + ".", ""
    result, line, _ = TL.run(vault, {"tool": tool, **args}, "owner")
    if tool == "open_app":
        if args.get("label") == "ссылка":
            return "Готово — открыла ссылку.", result
        shown = line.replace("Открыла: ", "")
        return (f"Готово — открыла {shown}." if shown else "Готово."), result
    if tool == "read_file":
        text = result.strip() or "(файл пустой)"
        return text[:1200] + ("\n…[файл длиннее]" if len(text) > 1200 else ""), result
    if tool == "list_files":
        text = result.strip() or "(пусто)"
        return text[:1000] + ("\n…[список обрезан]" if len(text) > 1000 else ""), result
    if tool == "find_files":
        return result.strip()[:1200] or "Ничего не нашла.", result
    if tool == "run_command":
        text = result.strip()
        return text[:1200] + ("\n…[вывод обрезан]" if len(text) > 1200 else ""), result
    return result.strip(), result


def _memory_on(vault: Vault) -> bool:
    from ..agent import profile as P

    return bool(P.memory_on(vault))


def answer(vault: Vault, call: dict) -> str:
    """Do the action and say one short line — the way the owner asked."""
    tool = call["tool"]
    if tool in ("read_file", "list_files", "find_files", "remember", "write_file", "make_document", "memory_find", "memory_show"):
        if not _is_tools_ok(vault, tool):
            return "Эти действия сейчас выключены в настройках."
    if tool in ("run_command", "open_app") and not _is_tools_ok(vault, tool):
        return "Доступ к компьютеру выключен в настройках."
    try:
        return _run(vault, tool, {k: v for k, v in call.items() if k not in ("tool", "label")})[0]
    except TL.Refused as e:
        return str(e)[:300]
    except Exception as e:  # a short command must never crash the chat
        return f"Не получилось: {str(e)[:200]}"


def _is_tools_ok(vault: Vault, tool: str) -> bool:
    from ..agent import profile as P

    prof = P.load(vault)
    if prof.get("tools") is False:
        return False
    if tool in ("run_command", "open_app") and prof.get("pc_access") is False:
        return False
    if tool == "remember" and not P.memory_on(vault):
        return False
    return True
