"""Actions in the chat: the model reads and writes files and memory — with the owner's word on every action.

Any model (Claude by subscription, a key, the built-in one) asks for an action with one block in its answer:

    ```mnema write_file path="C:\\Users\\me\\Documents\\plan.md"
    # План
    - первый шаг
    ```

Mnemai stops the answer there, shows the owner what is asked («Создать файл …» — Да / Нет / Да для этого разговора),
does it, gives the model the result and lets it go on. Files are read and written only in the memory folder and in the
work folders the owner added (Настройки → Программа → «Действия на компьютере»). The owner may also allow the terminal
(«pc_access», on by default): then the model can run one shell command at a time with a timeout and get its output.

Every write is in the journal and is undone from «История»: inside the memory folder like any memory write, outside
it with a snapshot of the file as it was. A document that would overwrite an existing one gets a new name instead.
A note of the memory folder is read under the rules of the AI that asks: hidden topics stay hidden.
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from pathlib import Path

from ..vault import Vault
from .. import osapi as OS

TOOLS = (
    "read_file",
    "list_files",
    "find_files",
    "write_file",
    "edit_file",
    "make_document",
    "edit_pdf",
    "remember",
    "run_command",
    "open_app",
)
WRITES = {"write_file", "edit_file", "make_document", "edit_pdf", "remember", "run_command", "open_app"}
TEXT_EXT = {".md", ".txt", ".csv", ".json", ".html", ".htm", ".xml", ".yml", ".yaml", ".log", ".ini", ".tsv"}
DOC_EXT = {".pdf", ".docx", ".xlsx", ".html", ".md", ".txt", ".csv"}
MAX_READ = 60_000
MAX_STEPS = 12
MAX_OUTPUT = 24_000
MAX_COMMAND_SECONDS = 300
DEFAULT_COMMAND_SECONDS = 120
BLOCK_RE = re.compile(r"```mnema[ \t]+(\w+)([^\n]*)\n?(.*?)(?:```|\Z)", re.S)
ARG_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')

RULE = """=== Действия на компьютере ===
У тебя ЕСТЬ доступ к компьютеру владельца: файлы и документы, а также терминал, если владелец не выключил его.
Чтобы сделать действие, напиши в ответе ОДИН блок и остановись — Mnemai спросит владельца (если он включил вопросы),
сделает и пришлёт результат, после чего ты продолжишь. Это настоящий доступ, а не описание: не говори «я не могу
запускать программы» — запусти и покажи результат. Если владелец просит сделать что-то на компьютере — сделай.

```mnema read_file path="полный путь"
```
(читает и PDF, Word, Excel, PowerPoint; сканы и картинки распознаются на компьютере)
```mnema list_files path="полный путь к папке"
```
```mnema find_files query="слова для поиска"
```
```mnema write_file path="полный путь к файлу .md, .txt, .csv, .json или .html"
весь текст файла
```
```mnema edit_file path="полный путь к текстовому файлу, .docx или .xlsx"
<<<
точный кусок, который заменить
===
чем заменить
>>>
```
(в Word заменяется текст с сохранением оформления; блоков <<< … >>> может быть несколько. В Excel можно и так —
по строке на ячейку: Лист1!B3 = 1500 или B3 = текст, формула начинается с =)
```mnema edit_pdf do="merge" files="путь1.pdf; путь2.pdf" path="полный путь к новому .pdf"
```
```mnema edit_pdf do="pages" from="исходный.pdf" pages="1-3, 7" path="новый .pdf"
```
(do="pages" — оставить эти страницы в этом порядке: так вырезают, удаляют и переставляют страницы;
do="rotate" — повернуть pages на angle="90", "180" или "270"; do="split" — разрезать: pages="1-3; 4-9", без pages —
по странице, path — папка. Исходные файлы не меняются, новый файл не затирает существующий)
```mnema make_document path="полный путь к .pdf, .docx или .xlsx"
содержимое в Markdown: заголовки #, списки -, таблицы |…|
```
```mnema remember where="card:Тема"
одна строка, которую записать в память
```
{terminal}
Где можно работать с файлами через read_file/write_file (только тут):
{folders}
Правила: одно действие за раз; путь — полностью, как в списке выше; не выводи в ответ пароли, ключи и токены; не делай
разрушительных действий без прямой просьбы (rm -rf, форматирование диска); не делай действий, о которых владелец не
просил; если владелец отказал — не повторяй то же самое. Когда всё сделано, ответь обычным текстом без блоков."""

TERMINAL_RULE = """```mnema run_command command="одна команда терминала" cwd="полный путь к папке" timeout="120"
```
(выполняет команду в терминале этого компьютера и возвращает вывод и код возврата; cwd — где выполнять, по умолчанию
домашняя папка; timeout — секунды, по умолчанию 120, максимум 300. Так можно смотреть процессы, железо, сеть, git,
запускать программы, ставить пакеты, работать с файлами вне рабочих папок — всё, что делает терминал.
Если команда сложная, пиши её в теле блока: ```mnema run_command cwd="…"``` и следующей строкой саму команду.
Терминал работает по всему компьютеру, а не только в папках памяти и рабочих папках.

```mnema open_app name="chrome"
```
(открывает программу или ссылку на этом компьютере: "chrome", "firefox", "telegram", "code", или https://… — Mnemai
сама найдёт установленную программу. Для «открой хром» используй это, а не догадки про имя команды в терминале.)"""

SMALL_RULE = """Файлы: чтобы прочитать файл, напиши блок ```mnema read_file path="путь"``` и остановись.
Чтобы создать файл: ```mnema write_file path="путь"``` с текстом внутри блока. Папки: {folders}
{terminal}"""


# ---------------------------------------------------------------- settings


def pc_enabled(vault: Vault) -> bool:
    """The owner allows commands on this computer (on by default)."""
    from ..agent import profile as P

    return bool(P.load(vault).get("tools", True)) and bool(P.load(vault).get("pc_access", True))


def enabled(vault: Vault) -> bool:
    """Actions are on and there is a place to act in (with memory off, only the work folders the owner added —
    and the terminal, if it is allowed, works everywhere)."""
    from ..agent import profile as P

    return bool(P.load(vault).get("tools", True)) and (bool(roots(vault)) or bool(P.load(vault).get("pc_access", True)))


def roots(vault: Vault) -> list[tuple[str, Path]]:
    """The memory folder first, then the work folders the owner added."""
    from ..agent import profile as P

    prof = P.load(vault)
    out = [("память", vault.root.resolve())] if prof.get("memory_on", True) else []
    for f in prof.get("tool_folders") or []:
        p = Path(str(f)).expanduser()
        if p.is_dir():
            out.append(("рабочая папка", p.resolve()))
    return out


def rule(vault: Vault, small: bool = False) -> str:
    folders = "\n".join(f"- {name}: {path}" for name, path in roots(vault))
    if pc_enabled(vault):
        terminal = (
            "Терминал: ```mnema run_command command=\"команда\"``` — выполнит её на этом компьютере и вернёт вывод. "
            "Это настоящий доступ."
            if small
            else TERMINAL_RULE
        )
    else:
        terminal = ""
    return (SMALL_RULE if small else RULE).format(folders=folders, terminal=terminal)


# ---------------------------------------------------------------- the block in the answer


def parse(text: str) -> dict | None:
    """The first action block in a model's answer: {"tool", args…, "body", "start"} or None."""
    m = BLOCK_RE.search(text or "")
    if not m or m.group(1) not in TOOLS:
        return None
    call = {k: v for k, v in ARG_RE.findall(m.group(2))}
    call.update(tool=m.group(1), body=(m.group(3) or "").rstrip("\n"), start=m.start())
    return call


def before(text: str, call: dict) -> str:
    """What the model said before its action block — shown to the owner, the block itself is not."""
    return text[: call["start"]].rstrip()


# ---------------------------------------------------------------- where it may act


class Refused(ValueError):
    pass


# documents «Открыть» may hand to their program; nothing that runs code
OPENABLE = {
    ".pdf",
    ".docx",
    ".doc",
    ".xlsx",
    ".xls",
    ".pptx",
    ".csv",
    ".md",
    ".txt",
    ".png",
    ".jpg",
    ".jpeg",
    ".odt",
    ".rtf",
}


def resolve(vault: Vault, path: str) -> Path:
    if not (path or "").strip():
        raise Refused("не указан путь")
    p = Path(path.strip().strip('"')).expanduser()
    if not p.is_absolute():
        p = vault.root / p
    p = p.resolve()
    for _, root in roots(vault):
        if p == root or root in p.parents:
            rel = p.relative_to(root).parts
            if root == vault.root.resolve() and rel and rel[0].startswith("."):
                raise Refused("служебная папка памяти закрыта")
            return p
    raise Refused("эта папка не открыта для действий. Добавить её можно в Настройки → Программа → «Действия на компьютере»")


def in_vault(vault: Vault, p: Path) -> str | None:
    root = vault.root.resolve()
    return p.relative_to(root).as_posix() if root in p.parents else None


def what(vault: Vault, call: dict) -> str:
    """The action in the owner's words, for the permission card."""
    t, path, q = call["tool"], call.get("path", ""), call.get("query", "")
    try:
        exists = resolve(vault, path).exists() if path else False
    except Refused:
        exists = False
    return {
        "read_file": f"прочитать файл {path}",
        "list_files": f"посмотреть, что лежит в папке {path}",
        "find_files": f"поискать «{q}» в файлах",
        "write_file": f"{'переписать' if exists else 'создать'} файл {path}",
        "edit_file": f"изменить файл {path}",
        "make_document": f"создать документ {path}",
        "edit_pdf": {
            "merge": f"склеить PDF ({call.get('files', '')}) в {path}",
            "pages": f"взять страницы {call.get('pages', '')} из {call.get('from', '')} в {path}",
            "rotate": f"повернуть страницы {call.get('pages') or 'все'} из {call.get('from', '')} в {path}",
            "split": f"разрезать {call.get('from', '')} на части в папку {path}",
        }.get(call.get("do", ""), f"изменить PDF {call.get('from', '')} → {path}"),
        "remember": f"записать в память ({call.get('where', 'inbox')}): «{call.get('body', '')[:200]}»",
        "run_command": f"выполнить в терминале: {_command(call)[:200]}",
        "open_app": f"открыть программу: {call.get('name', '')}",
    }[t]


# ---------------------------------------------------------------- doing it


def _read_any(p: Path, lang: str = "ru") -> str:
    from .. import docs
    from ..vault import read_text

    ext = p.suffix.lower()
    if ext in docs.IMAGES:
        text, _ = docs.extract(p, lang)
        return text or "(на картинке не нашлось текста)"
    if ext in docs.SUPPORTED and ext not in TEXT_EXT:
        text, _ = docs.extract(p, lang)
        return text
    return read_text(p)


def _read_note(vault: Vault, rel: str, client: str) -> str:
    """A note of the memory folder as this AI may see it."""
    from ..clients import get_client

    c = get_client(vault, client)
    n = vault.read(rel)
    if not c.allows(n.scope) and n.scope not in ("notes", "meetings"):
        raise Refused(f"эта часть памяти скрыта от этого ИИ ({n.scope})")
    return n.visible_text(set(c.deny_tags))


def _snapshot(
    vault: Vault, client: str, path: Path, before_bytes: bytes | None, after_bytes: bytes, summary: str
) -> dict:
    """A write outside the memory folder: in the journal with what was there before, so «История» can undo it."""
    from ..journal import _sdir, journal_line, log_event

    ev = log_event(
        vault,
        client,
        "write",
        summary,
        [str(path)],
        {"after": hashlib.sha256(after_bytes).hexdigest()[:16], "abs": True},
    )
    sd = _sdir(vault)
    sd.mkdir(parents=True, exist_ok=True)
    (sd / f"{ev['id']}.json").write_text(
        json.dumps(
            {
                "rel": str(path),
                "abs": True,
                "before_b64": base64.b64encode(before_bytes).decode() if before_bytes is not None else None,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    try:
        journal_line(vault, client, str(path), summary)
    except OSError:
        pass
    return ev


def read_only(vault: Vault, p: Path) -> bool:
    """A place Mnemai never writes to, whatever the folders for actions say: an Obsidian vault (a folder with
    .obsidian in it or above it) and the extra memory folders — Mnemai reads them and writes only into its own memory."""
    p = p.resolve()
    own = vault.root.resolve()
    if p == own or own in p.parents:
        return False
    from .. import extra
    from ..agent import profile as P

    for f in extra.folders(P.load(vault)):
        r = Path(f).expanduser().resolve()
        if p == r or r in p.parents:
            return True
    return any((d / ".obsidian").is_dir() for d in [p, *p.parents] if d != p or p.is_dir())


def _write_bytes(vault: Vault, client: str, p: Path, data: bytes, summary: str) -> None:
    if read_only(vault, p):
        raise Refused(
            "это хранилище Obsidian или дополнительная папка памяти — Mnemai их только читает и ничего в них не пишет"
        )
    rel = in_vault(vault, p)
    if rel and p.suffix.lower() == ".md":
        from ..journal import write_with_journal

        write_with_journal(vault, client, rel, data.decode("utf-8"), summary)
        return
    prev = p.read_bytes() if p.exists() else None
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + f".{uuid.uuid4().hex[:6]}.tmp")  # the bytes exactly as given, swapped in whole
    try:
        tmp.write_bytes(data)
        os.replace(tmp, p)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    _snapshot(vault, client, p, prev, data, summary)


def _free_name(p: Path) -> Path:
    """A document never overwrites one that is already there: «отчёт (2).pdf»."""
    if not p.exists():
        return p
    k = 2
    while True:
        q = p.with_name(f"{p.stem} ({k}){p.suffix}")
        if not q.exists():
            return q
        k += 1


def _command(call: dict) -> str:
    """The command as written: an argument, or the body of the block for multi-line scripts."""
    return " ".join(str(call.get("command") or call.get("body") or "").split())


def _run_command(vault: Vault, call: dict, client: str = "owner") -> tuple[str, str, str]:
    """Run one command in the owner's shell and turn its stdout/stderr/exit code into a short answer for the model.

    The terminal is a real PC access, so: a hard timeout (1–300 s), a process group killed on timeout, a bounded
    output, and every run in the journal («История»)."""
    from ..journal import log_event

    command = str(call.get("command") or call.get("body") or "").strip()
    if not command:
        raise Refused("пустая команда: нужен command=\"…\"")
    where = str(call.get("cwd") or "").strip()
    work = Path(where).expanduser().resolve() if where else Path.home()
    if not work.is_dir():
        raise Refused(f"нет такой папки для cwd: {work}")
    try:
        timeout = int(float(str(call.get("timeout") or DEFAULT_COMMAND_SECONDS).strip()))
    except ValueError:
        timeout = DEFAULT_COMMAND_SECONDS
    timeout = max(1, min(MAX_COMMAND_SECONDS, timeout))
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "NO_COLOR": "1", "TERM": "dumb"}
    started = time.time()
    if os.name == "nt":
        proc = subprocess.Popen(
            command,
            shell=True,
            cwd=work,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    else:
        shell = "/bin/bash" if Path("/bin/bash").exists() else "/bin/sh"
        proc = subprocess.Popen(
            [shell, "-lc", command],
            cwd=work,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            start_new_session=True,
        )
    timed_out = False
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            if os.name == "nt":
                proc.kill()
            else:
                os.killpg(proc.pid, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            pass
        try:
            out, err = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            out, err = "", ""
    seconds = time.time() - started
    log_event(vault, client, "exec", f"терминал ({timeout} с): {command[:160]}")
    code = proc.returncode
    head = f"[код {code} · {seconds:.1f} с · {work}]"
    if timed_out:
        head = f"[остановлена по таймауту {timeout} с · {work}]"
    parts = [head]
    if out.strip():
        parts.append("[вывод]\n" + out.strip())
    if err.strip():
        parts.append("[ошибки]\n" + err.strip())
    text = "\n".join(parts)
    if len(text) > MAX_OUTPUT:
        keep = MAX_OUTPUT - 200
        text = text[:keep].rstrip() + f"\n…[вывод обрезан: всего {len(text)} знаков]"
    if not out.strip() and not err.strip():
        text += "\n(команда ничего не вывела)"
    # the owner sees a short result right in the conversation, the model gets the whole (bounded) output
    shown = (out.strip() or err.strip()).splitlines()[:3]
    snippet = (" · ".join(x.strip() for x in shown)[:300] if shown else ("код " + str(code)))
    line = f"Выполнила команду: {command[:120]} → {snippet}"
    return text, line, str(work)


APP_ALIASES = {
    "chrome": ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"],
    "хром": ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"],
    "firefox": ["firefox", "firefox-esr"],
    "файрфокс": ["firefox", "firefox-esr"],
    "telegram": ["telegram-desktop", "telegram"],
    "телеграм": ["telegram-desktop", "telegram"],
    "code": ["code", "codium"],
    "vscode": ["code", "codium"],
    "terminal": ["konsole", "gnome-terminal", "xterm"],
    "терминал": ["konsole", "gnome-terminal", "xterm"],
}


def _open_app(vault: Vault, call: dict, client: str = "owner") -> tuple[str, str, str]:
    """Open a program or a link on this computer, detached from Mnemai."""
    import shutil

    from ..journal import log_event

    name = " ".join(str(call.get("name") or call.get("body") or "").split()).strip().strip('"')
    if not name:
        raise Refused("не указано, что открыть: name=\"chrome\" или name=\"https://…\"")
    log_event(vault, client, "exec", f"открыть: {name[:160]}")
    if name.startswith(("http://", "https://", "mailto:")):
        try:
            if os.name == "nt":
                os.startfile(name)  # noqa: S606 — opening a link is the point
            elif sys.platform == "darwin":
                subprocess.Popen(["open", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(
                    ["xdg-open", name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
        except OSError as e:
            raise Refused(f"не получилось открыть ссылку: {e}") from e
        return f"Открыла ссылку: {name}", f"Открыла ссылку: {name[:120]}", ""
    candidates = APP_ALIASES.get(name.lower(), [name])
    exe = next((shutil.which(c) for c in candidates if shutil.which(c)), None)
    if not exe:
        installed = [c for c in ("google-chrome", "chromium", "firefox", "code", "telegram-desktop") if shutil.which(c)]
        raise Refused(
            f"программа «{name}» не найдена. Установлены: {', '.join(installed) or 'не вижу известных программ'}"
        )
    try:
        if os.name == "nt":
            subprocess.Popen(
                [exe],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-a", exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(
                [exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True
            )
    except OSError as e:
        raise Refused(f"не получилось открыть «{name}»: {e}") from e
    shown = Path(exe).name
    return f"Открыла программу: {shown} ({exe})", f"Открыла: {shown}", str(Path(exe).parent)


def run(vault: Vault, call: dict, client: str = "owner") -> tuple[str, str, str]:
    """Do an approved action: (result for the model, line for the owner, path or "")."""
    t = call["tool"]
    if t == "remember":
        from ..agent import profile as P
        from ..memory import remember

        if not P.memory_on(vault):
            raise Refused(P.MEMORY_OFF)

        fact = " ".join(call.get("body", "").split())
        ev = remember(vault, fact, call.get("where") or "inbox", "owner")
        return f"Записано в память: {ev['paths'][0]}", f"Записала в память: «{fact[:120]}»", ""
    if t == "find_files":
        return _find(vault, call.get("query", "")), f"Поискала «{call.get('query', '')}» в файлах", ""
    if t == "run_command":
        if not pc_enabled(vault):
            raise Refused("терминал выключен владельцем: включить — Настройки → Программа → «Действия на компьютере»")
        return _run_command(vault, call, client)
    if t == "open_app":
        if not pc_enabled(vault):
            raise Refused("доступ к компьютеру выключен владельцем: включить — Настройки → Программа → «Действия на компьютере»")
        return _open_app(vault, call, client)
    p = resolve(vault, call.get("path", ""))
    if t == "list_files":
        if not p.is_dir():
            raise Refused("это не папка")
        items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))[:300]
        lines = [
            f"{'[папка] ' if x.is_dir() else ''}{x.name}{'' if x.is_dir() else f' · {x.stat().st_size} байт'}"
            for x in items
            if not x.name.startswith(".")
        ]
        return "\n".join(lines) or "(пусто)", f"Посмотрела папку {p}", str(p)
    if t == "read_file":
        if not p.is_file():
            raise Refused("такого файла нет")
        rel = in_vault(vault, p)
        from ..agent import profile as P

        lang = P.load(vault).get("lang") or "en"
        text = _read_note(vault, rel, client) if rel and p.suffix.lower() == ".md" else _read_any(p, lang)
        cut = len(text) > MAX_READ
        return (text[:MAX_READ] + ("\n…[файл длиннее, показано начало]" if cut else "")), f"Прочитала файл {p}", str(p)
    if t == "write_file":
        if p.suffix.lower() not in TEXT_EXT:
            raise Refused(
                "так пишутся только текстовые файлы (.md, .txt, .csv, .json, .html); документы — make_document"
            )
        existed = p.exists()
        _write_bytes(
            vault,
            client,
            p,
            call.get("body", "").encode("utf-8") + b"\n",
            f"{'переписан' if existed else 'создан'} файл {p.name}",
        )
        return f"Готово: {p}", f"{'Переписала' if existed else 'Создала'} файл {p}", str(p)
    if t == "edit_pdf":
        return _edit_pdf(vault, client, call, p)
    if t == "edit_file":
        if not p.is_file():
            raise Refused("такого файла нет")
        pairs = re.findall(r"<<<\n?(.*?)\n?===\n?(.*?)\n?>>>", call.get("body", ""), re.S)
        ext = p.suffix.lower()
        if ext == ".docx":
            if not pairs:
                raise Refused("не понятно, что на что заменить: нужен блок <<< … === … >>>")
            data, n = docx_replace(p.read_bytes(), pairs)
            if not n:
                raise Refused("такого текста в документе нет — прочитай файл и возьми текст точно")
            _write_bytes(vault, client, p, data, f"изменён документ {p.name}")
            return f"Готово: {p} (замен: {n})", f"Изменила документ {p}", str(p)
        if ext in (".xlsx", ".xlsm"):
            data, n = xlsx_edit(p, call.get("body", ""), pairs)
            if not n:
                raise Refused("нечего менять: нужны строки вида Лист1!B3 = 1500 или блок <<< … === … >>>")
            _write_bytes(vault, client, p, data, f"изменена таблица {p.name}")
            return f"Готово: {p} (изменено ячеек: {n})", f"Изменила таблицу {p}", str(p)
        if not pairs:
            raise Refused("не понятно, что на что заменить: нужен блок <<< … === … >>>")
        old, new = pairs[0]
        from ..vault import read_text

        cur = read_text(p)
        if old not in cur:
            raise Refused("такого куска в файле нет — прочитай файл и возьми текст точно")
        _write_bytes(vault, client, p, cur.replace(old, new, 1).encode("utf-8"), f"изменён файл {p.name}")
        return f"Готово: {p}", f"Изменила файл {p}", str(p)
    if t == "make_document":
        ext = p.suffix.lower()
        if ext not in DOC_EXT:
            raise Refused("документ может быть .pdf, .docx, .xlsx, .html, .md, .txt или .csv")
        p = _free_name(p)
        body = call.get("body", "")
        if ext == ".docx":
            data = docx_bytes(body)
        elif ext == ".xlsx":
            data = xlsx_bytes(body)
        elif ext == ".pdf":
            data = pdf_bytes(body)
        elif ext in (".html",):
            data = page_html(body).encode("utf-8")
        else:
            data = body.encode("utf-8")
        _write_bytes(vault, client, p, data, f"создан документ {p.name}")
        return f"Готово: {p}", f"Создала документ {p}", str(p)
    raise Refused("такого действия нет")


def _find(vault: Vault, query: str) -> str:
    words = [w.lower() for w in re.findall(r"\w{3,}", query or "")]
    if not words:
        raise Refused("нужны слова для поиска")
    hits, t0 = [], time.time()
    for _, root in roots(vault):
        for p in root.rglob("*"):
            if time.time() - t0 > 8 or len(hits) >= 40:
                break
            if any(part.startswith(".") for part in p.relative_to(root).parts) or not p.is_file():
                continue
            name = p.name.lower()
            score = sum(w in name for w in words)
            if p.suffix.lower() in (".md", ".txt") and p.stat().st_size < 2_000_000:
                try:
                    body = p.read_text(encoding="utf-8", errors="ignore").lower()
                    score += sum(w in body for w in words)
                except OSError:
                    pass
            if score:
                hits.append((score, str(p)))
    hits.sort(key=lambda h: -h[0])
    return "\n".join(path for _, path in hits[:40]) or "Ничего не нашлось."


# ---------------------------------------------------------------- documents from Markdown


def _inline(s: str) -> str:
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<i>\1</i>", s)


def _blocks(md: str) -> list[tuple[str, object]]:
    """Markdown → [("h1".."h3"|"p"|"li"|"table", content)]."""
    out, lines, i = [], (md or "").replace("\r\n", "\n").split("\n"), 0
    while i < len(lines):
        line = lines[i].rstrip()
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                    rows.append(cells)
                i += 1
            out.append(("table", rows))
            continue
        h = re.match(r"^(#{1,3})\s+(.*)", line)
        if h:
            out.append((f"h{len(h.group(1))}", h.group(2)))
        elif re.match(r"^\s*[-*•]\s+", line) or re.match(r"^\s*\d+[.)]\s+", line):
            out.append(("li", re.sub(r"^\s*([-*•]|\d+[.)])\s+", "", line)))
        elif line.strip():
            out.append(("p", line.strip()))
        i += 1
    return out


def page_html(md: str) -> str:
    parts = []
    for kind, c in _blocks(md):
        if kind == "table":
            rows = "".join(
                "<tr>"
                + "".join(f"<{'th' if k == 0 else 'td'}>{_inline(x)}</{'th' if k == 0 else 'td'}>" for x in r)
                + "</tr>"
                for k, r in enumerate(c)
            )
            parts.append(f"<table>{rows}</table>")
        elif kind == "li":
            parts.append(f"<ul><li>{_inline(c)}</li></ul>")
        else:
            parts.append(f"<{kind}>{_inline(c)}</{kind}>")
    body = "\n".join(parts).replace("</ul>\n<ul>", "")
    return (
        '<!doctype html><html lang="ru"><head><meta charset="utf-8"><style>'
        "body{font:11pt/1.5 'Segoe UI',Arial,sans-serif;color:#1d1d1f;margin:18mm}h1{font-size:20pt;margin:0 0 10pt}"
        "h2{font-size:15pt;margin:14pt 0 6pt}h3{font-size:12.5pt;margin:12pt 0 4pt}p{margin:0 0 6pt}ul{margin:0 0 6pt;padding-left:18pt}"
        "table{border-collapse:collapse;margin:6pt 0 10pt;width:100%}th,td{border:1px solid #c9c6bd;padding:4pt 6pt;text-align:left;vertical-align:top}"
        "th{background:#f1efe9}</style></head><body>" + body + "</body></html>"
    )


def edge_exe() -> str | None:
    return OS.chromium()


def pdf_bytes(md: str) -> bytes:
    """A PDF through a Chromium browser without its window: Edge, which every Windows 10 and 11 has, or Chrome."""
    exe = edge_exe()
    if not exe:
        raise Refused(
            "PDF делается через браузер Edge, Chrome или Chromium, а его на компьютере нет. Могу сделать .docx или .html"
        )
    d = Path(tempfile.mkdtemp(prefix="mnema-pdf-"))
    try:
        src, out = d / "doc.html", d / "doc.pdf"
        src.write_text(page_html(md), encoding="utf-8")
        subprocess.run(
            [
                exe,
                "--headless=new",
                "--disable-gpu",
                "--no-pdf-header-footer",
                f"--user-data-dir={d / 'profile'}",
                f"--print-to-pdf={out}",
                src.as_uri(),
            ],
            capture_output=True,
            timeout=90,
            **OS.quiet(),
        )
        if not out.exists() or out.stat().st_size < 200:
            raise Refused("PDF не собрался. Могу сделать .docx или .html")
        return out.read_bytes()
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _w(text: str, bold: bool = False, size: int = 0) -> str:
    rpr = ("<w:b/>" if bold else "") + (f'<w:sz w:val="{size}"/>' if size else "")
    runs = []
    for k, part in enumerate(re.split(r"(\*\*.+?\*\*)", text)):
        if not part:
            continue
        b = bold or (part.startswith("**") and part.endswith("**"))
        part = part.strip("*") if part.startswith("**") else part
        props = ("<w:b/>" if b else "") + (f'<w:sz w:val="{size}"/>' if size else "")
        runs.append(
            f'<w:r>{"<w:rPr>" + props + "</w:rPr>" if props else ""}<w:t xml:space="preserve">{html.escape(part)}</w:t></w:r>'
        )
    return f"<w:p>{''.join(runs) or f'<w:r><w:rPr>{rpr}</w:rPr><w:t></w:t></w:r>'}</w:p>"


def docx_bytes(md: str) -> bytes:
    body = []
    for kind, c in _blocks(md):
        if kind in ("h1", "h2", "h3"):
            body.append(_w(c, True, {"h1": 36, "h2": 30, "h3": 26}[kind]))
        elif kind == "li":
            body.append(_w("• " + c))
        elif kind == "table":
            border = (
                '<w:tblBorders>'
                + "".join(
                    f'<w:{s} w:val="single" w:sz="4" w:color="BFBFBF"/>'
                    for s in ("top", "left", "bottom", "right", "insideH", "insideV")
                )
                + "</w:tblBorders>"
            )
            rows = "".join(
                "<w:tr>" + "".join(f"<w:tc>{_w(x, k == 0)}</w:tc>" for x in r) + "</w:tr>" for k, r in enumerate(c)
            )
            body.append(f'<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/>{border}</w:tblPr>{rows}</w:tbl>')
        else:
            body.append(_w(c))
    doc = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
        + "".join(body)
        + "<w:sectPr/></w:body></w:document>"
    )
    buf = __import__("io").BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        )
        z.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        )
        z.writestr("word/document.xml", doc)
    return buf.getvalue()


def xlsx_bytes(md: str) -> bytes:
    """A table in Markdown (|…|) or CSV lines → a sheet."""
    from openpyxl import Workbook
    from openpyxl.styles import Font

    rows = next((c for k, c in _blocks(md) if k == "table"), None)
    if rows is None:
        rows = [[x.strip() for x in re.split(r"[;,\t]", line)] for line in (md or "").splitlines() if line.strip()]
    wb = Workbook()
    ws = wb.active
    for r in rows:
        ws.append([_num(x) for x in r])
    for cell in ws[1] if rows else []:
        cell.font = Font(bold=True)
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = min(
            60, max(10, max(len(str(c.value or "")) for c in col) + 2)
        )
    buf = __import__("io").BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _num(x: str):
    s = x.replace("\u00a0", "").replace(" ", "")
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d+[.,]\d+", s):
        return float(s.replace(",", "."))
    return x


# ---------------------------------------------------------------- PDF: merge, pages, rotate, split (pypdf)


def page_list(spec: str, total: int) -> list[int]:
    """«1-3, 7, 10-» → 0-based indexes in the order given. Empty or «все» → every page."""
    spec = (spec or "").strip().lower()
    if spec in ("", "все", "all"):
        return list(range(total))
    out = []
    for part in re.split(r"[,\s]+", spec):
        if not part:
            continue
        m = re.fullmatch(r"(\d+)?\s*[-–]\s*(\d+)?", part)
        if m:
            a = int(m.group(1) or 1)
            b = int(m.group(2) or total)
            step = 1 if a <= b else -1
            idx = range(a, b + step, step)
        elif part.isdigit():
            idx = [int(part)]
        else:
            raise Refused(f"не понятно, какие страницы: «{part}» — пиши так: 1-3, 7")
        for i in idx:
            if not 1 <= i <= total:
                raise Refused(f"в файле {total} стр., страницы {i} нет")
            out.append(i - 1)
    return out


def _pdf_reader(p: Path):
    from pypdf import PdfReader

    if p.suffix.lower() != ".pdf" or not p.is_file():
        raise Refused(f"нет такого PDF: {p}")
    r = PdfReader(str(p))
    if r.is_encrypted:
        try:
            ok = r.decrypt("")
        except Exception:
            ok = 0
        if not ok:
            raise Refused(f"PDF «{p.name}» защищён паролем")
    return r


def _pdf_bytes(writer) -> bytes:
    import io

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _edit_pdf(vault: Vault, client: str, call: dict, out: Path) -> tuple[str, str, str]:
    from pypdf import PdfWriter

    do = (call.get("do") or "").strip().lower()
    if do == "merge":
        files = [resolve(vault, f) for f in re.split(r"[;\n]+", call.get("files", "")) if f.strip()]
        if len(files) < 2:
            raise Refused("для склейки нужно два PDF или больше: files=\"путь1.pdf; путь2.pdf\"")
        w = PdfWriter()
        for f in files:
            w.append(_pdf_reader(f))
        made = [(out, _pdf_bytes(w))]
    elif do in ("pages", "rotate", "split"):
        src = resolve(vault, call.get("from", ""))
        r = _pdf_reader(src)
        total = len(r.pages)
        if do == "split":
            groups = [g for g in (call.get("pages") or "").split(";") if g.strip()]
            parts = [page_list(g, total) for g in groups] if groups else [[i] for i in range(total)]
            folder = out if not out.suffix else out.parent
            made = []
            for idx in parts:
                w = PdfWriter()
                for i in idx:
                    w.add_page(r.pages[i])
                label = f"{idx[0] + 1}" if len(idx) == 1 else f"{idx[0] + 1}-{idx[-1] + 1}"
                made.append((folder / f"{src.stem} — стр. {label}.pdf", _pdf_bytes(w)))
        else:
            w = PdfWriter()
            if do == "pages":
                for i in page_list(call.get("pages", ""), total):
                    w.add_page(r.pages[i])
            else:
                angle = int(re.sub(r"\D", "", call.get("angle") or "90") or 90)
                if angle % 90:
                    raise Refused("повернуть можно на 90, 180 или 270")
                turn = set(page_list(call.get("pages", ""), total))
                for i, pg in enumerate(r.pages):
                    w.add_page(pg)
                    if i in turn:
                        w.pages[-1].rotate(angle)
            made = [(out, _pdf_bytes(w))]
    else:
        raise Refused("edit_pdf умеет do=\"merge\", \"pages\", \"rotate\" или \"split\"")
    names = []
    for target, data in made:
        if target.suffix.lower() != ".pdf":
            raise Refused("новый файл должен быть .pdf")
        resolve(vault, str(target))  # inside the open folders
        target = _free_name(target)
        _write_bytes(vault, client, target, data, f"создан PDF {target.name}")
        names.append(str(target))
    line = f"Сделала PDF {names[0]}" if len(names) == 1 else f"Сделала {len(names)} PDF в папке {Path(names[0]).parent}"
    return "Готово:\n" + "\n".join(names), line, names[0]


# ---------------------------------------------------------------- Word and Excel: change what is there


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
DOCX_PARTS = re.compile(r"word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml$")


def _rezip(data: bytes, changed: dict[str, bytes]) -> bytes:
    """The same package with some parts replaced; everything else byte for byte."""
    import io

    src = zipfile.ZipFile(io.BytesIO(data))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            dst.writestr(info, changed.get(info.filename, src.read(info.filename)))
    return buf.getvalue()


def docx_replace(data: bytes, pairs: list[tuple[str, str]]) -> tuple[bytes, int]:
    """Replace text in a Word document keeping its formatting: a phrase split over several runs (bold word inside,
    spell-check marks) is found too; the new text takes the format of where the old one began."""
    import io

    from lxml import etree

    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise Refused("файл .docx повреждён или это не документ Word") from None
    w = "{%s}" % W_NS
    path = "./w:r/w:t | ./w:hyperlink/w:r/w:t | ./w:ins/w:r/w:t | ./w:smartTag/w:r/w:t | ./w:sdt/w:sdtContent/w:r/w:t"
    changed, count = {}, 0
    for name in z.namelist():
        if not DOCX_PARTS.match(name):
            continue
        root = etree.fromstring(z.read(name))
        n_here = 0
        for para in root.iter(w + "p"):
            ts = para.xpath(path, namespaces={"w": W_NS})
            if not ts:
                continue
            for old, new in pairs:
                if not old:
                    continue
                start = 0
                while True:
                    full = "".join(t.text or "" for t in ts)
                    i = full.find(old, start)
                    if i < 0:
                        break
                    j, pos, first = i + len(old), 0, True
                    for t in ts:
                        s = t.text or ""
                        a, b = pos, pos + len(s)
                        pos = b
                        if b <= i or a >= j or (a == b):
                            continue
                        lo, hi = max(i, a) - a, min(j, b) - a
                        t.text = s[:lo] + (new if first else "") + s[hi:]
                        t.set(XML_SPACE, "preserve")
                        first = False
                    start = i + len(new)
                    n_here += 1
        if n_here:
            changed[name] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            count += n_here
    return (_rezip(data, changed) if changed else data), count


CELL_RE = re.compile(r"^\s*(?:(?:'([^']+)'|([^!=\s][^!=]*?))!)?\$?([A-Za-z]{1,3})\$?(\d{1,7})\s*=\s?(.*)$")


def xlsx_edit(p: Path, body: str, pairs: list[tuple[str, str]]) -> tuple[bytes, int]:
    """Set cells («Лист1!B3 = 1500», «B3 = текст», «C7 = =SUM(C1:C6)») and/or replace text in text cells. Formulas,
    formats and the other sheets stay. A book with charts or pictures is refused: they would be lost on saving."""
    import io

    from openpyxl import load_workbook

    with zipfile.ZipFile(p) as z:
        if any(n.startswith(("xl/charts/", "xl/drawings/", "xl/pivotTables/")) for n in z.namelist()):
            raise Refused(
                "в этой книге есть графики, картинки или сводные таблицы — при правке они пропадут. "
                "Попроси владельца поправить её в Excel или сделай новую таблицу через make_document"
            )
    wb = load_workbook(p, keep_vba=p.suffix.lower() == ".xlsm")
    n = 0
    text_part = re.sub(r"<<<.*?>>>", "", body or "", flags=re.S)
    for line in text_part.splitlines():
        if not line.strip():
            continue
        m = CELL_RE.match(line)
        if not m:
            raise Refused(f"не понятна строка «{line.strip()[:80]}» — пиши так: Лист1!B3 = 1500")
        sheet = m.group(1) or m.group(2)
        if sheet and sheet not in wb.sheetnames:
            raise Refused(f"листа «{sheet}» нет. Листы: {', '.join(wb.sheetnames)}")
        ws = wb[sheet] if sheet else wb.active
        raw = m.group(5).rstrip()
        ws[f"{m.group(3).upper()}{m.group(4)}"] = raw if raw.startswith("=") else _num(raw) if raw else None
        n += 1
    for old, new in pairs:
        if not old:
            continue
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for c in row:
                    if isinstance(c.value, str) and not c.value.startswith("=") and old in c.value:
                        c.value = c.value.replace(old, new)
                        n += 1
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue(), n
