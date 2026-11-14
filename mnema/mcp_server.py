"""MCP server over stdio: lets Claude (Desktop, Code) and other MCP clients use the memory.

JSON-RPC 2.0, one message per line, UTF-8. Standard library only.
Run: python -m mnema mcp --client claude [--vault PATH]
"""

from __future__ import annotations

import json
import shutil
import sys
import urllib.parse
from pathlib import Path

from . import __version__
from .clients import get_client
from .journal import UndoError, events, log_event, undo
from .memory import PermissionDenied, context_for, remember
from .vault import Vault

PROTOCOLS = ["2025-06-18", "2025-03-26", "2024-11-05"]

INSTRUCTIONS = (
    "Это память владельца: кто он, его правила, проекты, люди и решения. "
    "В начале разговора вызови memory_context и опирайся на неё, не переспрашивай известное. "
    "Когда в разговоре появилось что-то долговечное (решение, договорённость, новый факт о человеке или проекте), "
    "предложи сохранить и вызови memory_remember. Перед ответом на устаревший факт вызови memory_stale. "
    "У тебя также ЕСТЬ доступ к компьютеру владельца (если он не выключил его в настройках): терминал — pc_run, "
    "файлы — pc_read_file и pc_write_file, папки — pc_list_dir, перенос/копирование/удаление — pc_move/pc_copy/"
    "pc_delete; поиск в интернете — web_search и web_fetch; уведомление — pc_notify, снимок экрана — pc_screenshot. "
    "Это настоящий доступ, а не описание. Файлы памяти доступны и как ресурсы (mnema://memory/…), а промпты "
    "memory_brief и remember_fact помогают начать. Когда просят "
    "что-то сделать на компьютере, выполни команду и покажи результат. Не выводи пароли и ключи."
)

TOOLS = [
    {
        "name": "memory_context",
        "description": "Загрузить память владельца (профиль, правила, проекты, решения — что разрешено этому ассистенту). "
        "Вызывай в начале разговора. Большая память отдаётся частями: part=0, 1, 2…",
        "inputSchema": {"type": "object", "properties": {"part": {"type": "integer", "minimum": 0, "default": 0}}},
    },
    {
        "name": "memory_search",
        "description": "Найти в памяти строки по словам. Возвращает файл и строку.",
        "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    },
    {
        "name": "memory_remember",
        "description": "Сохранить факт в память. where: inbox (по умолчанию), decisions, rules, project:<имя>, person:<имя>. "
        "Сохраняй только долговечное и только то, что владелец подтвердил.",
        "inputSchema": {
            "type": "object",
            "properties": {"fact": {"type": "string"}, "where": {"type": "string", "default": "inbox"}},
            "required": ["fact"],
        },
    },
    {
        "name": "memory_stale",
        "description": "Факты и проекты, которые давно не обновлялись. Используй, чтобы не опираться на устаревшее.",
        "inputSchema": {"type": "object", "properties": {"days": {"type": "integer", "default": 30}}},
    },
    {
        "name": "memory_journal",
        "description": "Последние события памяти: кто что прочитал и записал.",
        "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer", "default": 20}}},
    },
    {
        "name": "memory_undo",
        "description": "Откатить запись по id из журнала. Только если владелец попросил.",
        "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
    },
    {
        "name": "memory_forget",
        "description": "Забыть факт: по id записи журнала (id=…) или по словам (query=…). Факт уходит в архив, "
        "ассистентам больше не показывается. Только если владелец попросил.",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string"}, "query": {"type": "string"}},
        },
    },
    {
        "name": "memory_update",
        "description": "Заменить факт: найти старое по словам (query=…) и записать новое (text=…). where — куда положить "
        "новое: inbox (по умолчанию), decisions, rules, project:<имя>, person:<имя>, card:<тема>.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "text": {"type": "string"},
                "where": {"type": "string", "default": "inbox"},
            },
            "required": ["query", "text"],
        },
    },
    {
        "name": "web_search",
        "description": "Найти страницы в интернете без ключей: возвращает заголовки, ссылки и фрагменты. Поиск "
        "записывается в «Что ушло наружу».",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 10, "default": 6},
            },
            "required": ["query"],
        },
    },
    {
        "name": "web_fetch",
        "description": "Открыть страницу по ссылке и вернуть её текст (очищенный от разметки).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "max_chars": {"type": "integer", "minimum": 1000, "maximum": 120000},
            },
            "required": ["url"],
        },
    },
    {
        "name": "pc_make_dir",
        "description": "Создать папку на компьютере (вместе с родительскими).",
        "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    },
    {
        "name": "pc_move",
        "description": "Перенести/переименовать файл или папку на компьютере.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "destination": {"type": "string"}},
            "required": ["path", "destination"],
        },
    },
    {
        "name": "pc_copy",
        "description": "Скопировать файл или папку на компьютере.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "destination": {"type": "string"}},
            "required": ["path", "destination"],
        },
    },
    {
        "name": "pc_delete",
        "description": "Удалить файл или папку в корзину (обратимо). Только если владелец попросил.",
        "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    },
    {
        "name": "pc_notify",
        "description": "Показать системное уведомление на компьютере владельца (например, «задача готова»).",
        "inputSchema": {
            "type": "object",
            "properties": {"title": {"type": "string"}, "text": {"type": "string"}},
            "required": ["title"],
        },
    },
    {
        "name": "pc_screenshot",
        "description": "Сделать снимок экрана и вернуть путь к файлу (по умолчанию в Изображения/Mnemai).",
        "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}},
    },
    {
        "name": "pc_run",
        "description": "Выполнить команду в терминале этого компьютера и вернуть вывод, код возврата и время. "
        "Это настоящий доступ к системе (процессы, железо, сеть, git, файлы вне папок памяти). "
        "Одна команда за раз, таймаут по умолчанию 120 с, максимум 300 с.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "cwd": {"type": "string"},
                "timeout": {"type": "integer", "minimum": 1, "maximum": 300, "default": 120},
                "terminal": {
                    "type": "boolean",
                    "description": "Показать команду в видимом терминале (для установки и sudo).",
                },
            },
            "required": ["command"],
        },
    },
    {
        "name": "pc_read_file",
        "description": "Прочитать текстовый файл с компьютера (до 60 000 знаков).",
        "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    },
    {
        "name": "pc_write_file",
        "description": "Записать текст в файл на компьютере (перезаписывает существующий).",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "text": {"type": "string"}},
            "required": ["path", "text"],
        },
    },
    {
        "name": "pc_list_dir",
        "description": "Показать, что лежит в папке на компьютере.",
        "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}},
    },
    {
        "name": "pc_open_app",
        "description": "Открыть программу или ссылку на компьютере владельца (chrome, firefox, telegram, https://…).",
        "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
    },
]


ACTION_TOOLS = [
    {
        "name": "read_file",
        "description": "Прочитать файл в памяти или в рабочих папках (PDF, Word, Excel, PowerPoint, сканы — тоже).",
        "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    },
    {
        "name": "list_files",
        "description": "Показать, что лежит в папке памяти или в рабочей папке.",
        "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    },
    {
        "name": "find_files",
        "description": "Найти файлы по словам в памяти и рабочих папках.",
        "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    },
    {
        "name": "write_file",
        "description": "Создать или переписать текстовый файл (.md, .txt, .csv, .json, .html).",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "body": {"type": "string"}},
            "required": ["path", "body"],
        },
    },
    {
        "name": "edit_file",
        "description": "Заменить кусок в текстовом файле, .docx или .xlsx (блок <<< … === … >>>).",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "body": {"type": "string"}},
            "required": ["path", "body"],
        },
    },
    {
        "name": "make_document",
        "description": "Создать PDF, Word или Excel из Markdown-текста.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "body": {"type": "string"}},
            "required": ["path", "body"],
        },
    },
    {
        "name": "edit_pdf",
        "description": "Склеить, вырезать страницы, повернуть или разрезать PDF (do=merge|pages|rotate|split).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "do": {"type": "string"},
                "path": {"type": "string"},
                "from": {"type": "string"},
                "pages": {"type": "string"},
                "files": {"type": "string"},
                "angle": {"type": "string"},
            },
        },
    },
    {
        "name": "run_command",
        "description": "Выполнить команду в терминале компьютера (то же, что pc_run).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "cwd": {"type": "string"},
                "timeout": {"type": "integer", "minimum": 1, "maximum": 300, "default": 120},
            },
            "required": ["command"],
        },
    },
    {
        "name": "open_app",
        "description": "Открыть программу, файл, папку или ссылку (то же, что pc_open_app).",
        "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
    },
]
PC_WRITE = {"pc_run", "pc_write_file", "pc_open_app", "pc_make_dir", "pc_move", "pc_copy", "pc_delete", "pc_screenshot"}
ACTION_NAMES = {t["name"] for t in ACTION_TOOLS}
WRITE_ACTIONS = {"write_file", "edit_file", "make_document", "edit_pdf"}

TOOLS += ACTION_TOOLS


def run_action(vault: Vault, call: dict, client: str = "owner") -> tuple[str, str, str]:
    """The one place where a model's action is executed: the MCP server and the chat both go through it."""
    from .chat import tools as TL

    return TL.run(vault, call, client)


PROMPTS = [
    {
        "name": "memory_brief",
        "description": "Кратко собрать контекст владельца из памяти.",
        "arguments": [],
    },
    {
        "name": "remember_fact",
        "description": "Проверить и сохранить долговечный факт в память.",
        "arguments": [{"name": "fact", "description": "Что запомнить", "required": True}],
    },
]


class Server:
    def __init__(self, vault: Vault, client_id: str):
        self.vault = vault
        self.client_id = client_id

    # -- tools
    def call(self, name: str, args: dict) -> str:
        if (self.vault.service / "crypto.json").exists():  # encrypted (maybe after this server started): its key
            from . import crypt

            if crypt.attach(self.vault.root) == "locked":
                return "Память зашифрована: открой Mnemai и введи пароль — тогда память снова доступна."
        c = get_client(self.vault, self.client_id)
        if not c.enabled:
            return "Доступ к памяти для этого ассистента выключен владельцем."
        from .agent import profile as P

        if name.startswith("memory_") and not P.memory_on(self.vault):
            return P.MEMORY_OFF
        if name == "memory_forget":
            if not c.can_write:
                raise PermissionDenied(f"{c.name} не может удалять записи")
            return self._forget(args, c)
        if name == "memory_update":
            if not c.can_write:
                raise PermissionDenied(f"{c.name} не может менять записи")
            return self._update_memory(args, c)
        if name in ("web_search", "web_fetch"):
            return self._web(name, args)
        if name in ACTION_NAMES:
            if not P.load(self.vault).get("tools", True):
                return "Действия выключены владельцем: Настройки → Программа → «Действия на компьютере»."
            if name in WRITE_ACTIONS and not c.can_write:
                raise PermissionDenied(f"{c.name} не может менять файлы")
            return run_action(self.vault, {"tool": name, **args}, self.client_id)[0]
        if name == "memory_context":
            part = int(args.get("part", 0) or 0)
            text, total = context_for(self.vault, self.client_id, part=part)
            if not text:
                return f"Частей всего {total}, части {part} нет."
            if part + 1 < total:
                text += f"\n\n[Есть ещё части: вызови memory_context с part={part + 1}]"
            return text
        if name == "memory_search":
            hits = self.vault.search(str(args.get("query", "")), scopes=set(c.scopes), deny_tags=set(c.deny_tags))
            log_event(
                self.vault, self.client_id, "read", f"поиск: {args.get('query', '')}", sorted({r for r, _ in hits})
            )
            return "\n".join(f"{rel}: {line}" for rel, line in hits) or "Ничего не нашлось."
        if name == "memory_remember":
            ev = remember(
                self.vault, str(args.get("fact", "")), str(args.get("where", "inbox") or "inbox"), self.client_id
            )
            return f"Сохранено (id {ev['id']}, {ev['paths'][0]}). Откатить: memory_undo id={ev['id']}."
        if name == "memory_stale":
            days = int(args.get("days", 30) or 30)
            items = [
                s
                for s in self.vault.stale(max_age_days=days)
                if c.allows(self.vault.read(s.rel).scope) and not (s.tags & set(c.deny_tags))
            ]
            return "\n".join(f"- {s.text} — {s.age_days} дн. ({s.rel})" for s in items) or "Устаревшего нет."
        if name == "memory_journal":
            evs = [e for e in events(self.vault, 500) if self._may_see(e, c)][: int(args.get("limit", 20) or 20)]
            return (
                "\n".join(f"{e['ts']} · {e['client']} · {e['action']} · {e['summary']} · id {e['id']}" for e in evs)
                or "Журнал пуст."
            )
        if name.startswith("pc_"):
            return self._pc(name, args, c)
        if name == "memory_undo":
            if not c.can_write:
                raise PermissionDenied(f"{c.name} не может откатывать записи")
            ev = next((e for e in events(self.vault, 100000) if e["id"] == str(args.get("id", ""))), None)
            if ev and ev.get("client") != self.client_id:  # only its own writes; the owner's and others' stay
                raise PermissionDenied(f"{c.name} может откатывать только свои записи")
            ev = undo(self.vault, str(args.get("id", "")), self.client_id)
            return f"Откачено: {ev['summary']}"
        raise KeyError(name)

    def _pc(self, name: str, args: dict, c) -> str:
        """The owner's computer through MCP: the same terminal as in the chat, with the same journal. Reading needs
        the assistant to be enabled; running and writing also need its write permission."""
        from .agent import profile as P

        if not P.load(self.vault).get("pc_access", True):
            raise PermissionDenied(
                "доступ к компьютеру выключен владельцем: Настройки → Программа → «Действия на компьютере»"
            )
        from .chat import tools as TL
        from .journal import log_event

        if name in PC_WRITE and not c.can_write:
            raise PermissionDenied(f"{c.name} не может менять файлы, запускать команды и программы")
        if name == "pc_run":
            cmd = str(args.get("command") or "").strip()
            if not cmd:
                raise ValueError("нужна команда")
            call = {"tool": "run_command", "command": cmd, "timeout": args.get("timeout")}
            if args.get("cwd"):
                call["cwd"] = str(args["cwd"])
            return TL._run_command(self.vault, call, self.client_id)[0]
        if name == "pc_read_file":
            p = Path(str(args.get("path") or "")).expanduser()
            if not p.is_file():
                raise ValueError("такого файла нет")
            data = p.read_bytes()[: TL.MAX_READ]
            log_event(self.vault, self.client_id, "read", f"файл {p}", [])
            return data.decode("utf-8", "replace")
        if name == "pc_open_app":
            opened = TL.run(self.vault, {"tool": "open_app", "name": str(args.get("name") or "")}, self.client_id)
            return opened[0]
        if name == "pc_list_dir":
            p = Path(str(args.get("path") or "~")).expanduser()
            if not p.is_dir():
                raise ValueError("такой папки нет")
            items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))[:300]
            return (
                "\n".join(
                    f"{'[папка] ' if x.is_dir() else ''}{x.name}{'' if x.is_dir() else f' · {x.stat().st_size} байт'}"
                    for x in items
                    if not x.name.startswith(".")
                )
                or "(пусто)"
            )
        if name == "pc_make_dir":
            p = Path(str(args.get("path") or "")).expanduser()
            p.mkdir(parents=True, exist_ok=True)
            log_event(self.vault, self.client_id, "exec", f"создана папка {p}")
            return f"Папка создана: {p}"
        if name in ("pc_move", "pc_copy"):
            src = Path(str(args.get("path") or "")).expanduser()
            dst = Path(str(args.get("destination") or "")).expanduser()
            if not src.exists():
                raise ValueError("такого файла или папки нет")
            if dst.exists():
                raise ValueError("место назначения уже существует")
            dst.parent.mkdir(parents=True, exist_ok=True)
            if name == "pc_move":
                shutil.move(str(src), str(dst))
                log_event(self.vault, self.client_id, "exec", f"перенесено {src} → {dst}")
                return f"Перенесено: {src} → {dst}"
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            log_event(self.vault, self.client_id, "exec", f"скопировано {src} → {dst}")
            return f"Скопировано: {src} → {dst}"
        if name == "pc_delete":
            from . import osapi as OS

            p = Path(str(args.get("path") or "")).expanduser()
            if not p.exists():
                raise ValueError("такого файла или папки нет")
            if not OS.to_trash(p):
                raise ValueError("не получилось отправить в корзину")
            log_event(self.vault, self.client_id, "exec", f"в корзину: {p}")
            return f"В корзине: {p}"
        if name == "pc_notify":
            from . import osapi as OS

            ok = OS.notify(str(args.get("title") or "Mnemai"), str(args.get("text") or ""))
            return "Уведомление показано." if ok else "На этом компьютере нет системных уведомлений."
        if name == "pc_screenshot":
            from . import osapi as OS

            shot = OS.screenshot(args.get("path") or None)
            if not shot:
                raise ValueError("не получилось сделать снимок экрана")
            log_event(self.vault, self.client_id, "read", f"снимок экрана {shot}")
            return f"Снимок экрана: {shot}"
        if name == "pc_write_file":
            p = Path(str(args.get("path") or "")).expanduser()
            if not p.parent.is_dir():
                raise ValueError("такой папки нет")
            text = str(args.get("text") or "")
            # the same write path as the chat: a snapshot and a journal line, so «История» can undo it
            TL._write_bytes(self.vault, self.client_id, p, text.encode("utf-8"), f"записан файл {p.name}")
            return f"Записано: {p} (откат — «Память» → «История»)"
        raise KeyError(name)

    def _forget(self, args: dict, c) -> str:
        from . import memory as MEM
        from .journal import events as evs

        eid = str(args.get("id") or "").strip()
        if eid:
            ev = next((e for e in evs(self.vault, 100000) if e["id"] == eid), None)
            if not ev:
                raise ValueError("такой записи нет")
            if ev.get("client") != self.client_id:
                raise PermissionDenied(f"{c.name} может забывать только свои записи")
            done = undo(self.vault, eid, self.client_id)
            return f"Забыто: {done['summary']}"
        query = str(args.get("query") or "").strip()
        if not query:
            raise ValueError("нужен id или query")
        hits = self.vault.search(query, scopes=set(c.scopes), deny_tags=set(c.deny_tags))
        if not hits:
            return "Ничего не нашлось."
        gone: list[str] = []
        for rel, line in hits:
            raw = self.vault.read_raw(rel)
            if not raw:
                continue
            target = line.strip()
            lines = raw.splitlines()
            if target not in [ln.strip() for ln in lines]:
                continue
            MEM._archive_lines(self.vault, rel, [line], "забыто по просьбе владельца")
            rest = [ln for ln in lines if ln.strip() != target]
            self.vault.write_raw(rel, "\n".join(rest) + "\n")
            log_event(self.vault, self.client_id, "forget", f"забыто: {query}", [rel])
            gone.append(f"- {line.strip()} ({rel})")
        if gone:
            try:
                MEM.generate_now(self.vault)
                MEM.generate_index(self.vault)
            except Exception:  # noqa: BLE001 — the files are already changed; the summary is best effort
                pass
        return "Забыто:\n" + "\n".join(gone[:20]) if gone else "Ничего не нашлось."

    def _update_memory(self, args: dict, c) -> str:
        query = str(args.get("query") or "").strip()
        text = str(args.get("text") or "").strip()
        where = str(args.get("where") or "inbox")
        if not query or not text:
            raise ValueError("нужны query и text")
        gone = self._forget({"query": query}, c)
        if "Ничего" in gone:
            return gone
        remember(self.vault, text, where, self.client_id)
        return f"Заменено. {gone}\n\nЗаписано: {text[:200]} ({where})"

    def _web(self, name: str, args: dict) -> str:
        from . import outgoing as OG, web

        if name == "web_search":
            query = str(args.get("query") or "").strip()
            if not query:
                raise ValueError("нужен query")
            limit = max(1, min(10, int(args.get("limit") or 6)))
            hits = web.search(query, limit)
            OG.log(self.vault, "web", "", len(query), {}, {"purpose": "MCP web_search", "client": self.client_id})
            if not hits:
                return "Ничего не нашлось."
            return "\n".join(
                f"{k + 1}. {h['title']}\n   {h['url']}\n   {h.get('snippet', '')[:300]}" for k, h in enumerate(hits)
            )
        url = str(args.get("url") or "").strip()
        if not web.public_url(url):
            raise ValueError("эта ссылка не годится")
        doc = web.fetch(url)
        OG.log(self.vault, "web", "", len(url), {}, {"purpose": "MCP web_fetch", "client": self.client_id})
        cap = max(1000, min(120000, int(args.get("max_chars") or 60000)))
        return f"{doc.get('title') or url}\n{doc.get('url') or url}\n\n{(doc.get('text') or '')[:cap]}"

    def _resources(self) -> list[dict]:
        c = get_client(self.vault, self.client_id)
        out: list[dict] = []
        try:
            files = sorted(self.vault.root.rglob("*.md"))
        except OSError:
            return out
        for p in files[:400]:
            rel = p.relative_to(self.vault.root).as_posix()
            if rel.startswith((".", "90 System/")) or "Fact archive" in rel:
                continue
            try:
                note = self.vault.read(rel)
            except (OSError, ValueError):
                continue
            if not c.allows(note.scope) or (note.tags & set(c.deny_tags)):
                continue
            out.append(
                {
                    "uri": "mnema://memory/" + urllib.parse.quote(rel),
                    "name": rel,
                    "title": rel,
                    "mimeType": "text/markdown",
                }
            )
        return out

    def _resource_read(self, uri: str) -> dict:
        if not uri.startswith("mnema://memory/"):
            raise ValueError("неизвестный ресурс")
        rel = urllib.parse.unquote(uri[len("mnema://memory/") :])
        if not rel or ".." in rel:
            raise ValueError("плохой путь")
        c = get_client(self.vault, self.client_id)
        note = self.vault.read(rel)
        if not c.allows(note.scope) or (note.tags & set(c.deny_tags)):
            raise PermissionDenied(f"{c.name} не может читать этот файл")
        text = self.vault.read_raw(rel) or ""
        log_event(self.vault, self.client_id, "read", f"ресурс {rel}", [rel])
        return {"contents": [{"uri": uri, "mimeType": "text/markdown", "text": text}]}

    def _prompt_get(self, p: dict) -> dict:
        name = str(p.get("name") or "")
        args = p.get("arguments") or {}
        if name == "memory_brief":
            text = "Вызови memory_context и кратко перескажи, что важно знать о владельце и его проектах."
        elif name == "remember_fact":
            fact = str(args.get("fact") or "").strip()
            if not fact:
                raise ValueError("нужен аргумент fact")
            text = f"Сохрани в память этот факт, если он долговечен: {fact}"
        else:
            raise ValueError(f"неизвестный промпт: {name}")
        return {"description": name, "messages": [{"role": "user", "content": {"type": "text", "text": text}}]}

    def _may_see(self, ev: dict, c) -> bool:
        """A journal line only about what this assistant may read: no hidden tags, no hidden notes, allowed scopes."""
        from .vault import line_tags

        deny = set(c.deny_tags)
        if line_tags(ev.get("summary", "")) & deny:
            return False
        for rel in ev.get("paths") or []:
            try:
                n = self.vault.read(rel) if rel.endswith(".md") and self.vault.read_raw(rel) is not None else None
            except (OSError, ValueError):
                n = None
            if n is not None and ((n.tags & deny) or not c.allows(n.scope)):
                return False
        return True

    # -- protocol
    def handle(self, msg: dict) -> dict | None:
        method, mid = msg.get("method"), msg.get("id")
        if mid is None:  # notification
            return None
        try:
            if method == "initialize":
                asked = (msg.get("params") or {}).get("protocolVersion")
                result = {
                    "protocolVersion": asked if asked in PROTOCOLS else PROTOCOLS[0],
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                        "prompts": {"listChanged": False},
                    },
                    "serverInfo": {"name": "mnemai", "version": __version__},
                    "instructions": INSTRUCTIONS,
                }
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": TOOLS}
            elif method == "tools/call":
                p = msg.get("params") or {}
                name = p.get("name")
                if name not in {t["name"] for t in TOOLS}:
                    return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": f"unknown tool {name}"}}
                try:
                    text, is_error = self.call(name, p.get("arguments") or {}), False
                except (PermissionDenied, UndoError, ValueError) as e:
                    text, is_error = f"Ошибка: {e}", True
                result = {"content": [{"type": "text", "text": text}], "isError": is_error}
            elif method == "resources/list":
                result = {"resources": self._resources()}
            elif method == "resources/read":
                result = self._resource_read(str((msg.get("params") or {}).get("uri") or ""))
            elif method == "prompts/list":
                result = {"prompts": PROMPTS}
            elif method == "prompts/get":
                result = self._prompt_get(msg.get("params") or {})
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": mid,
                    "error": {"code": -32601, "message": f"method not found: {method}"},
                }
            return {"jsonrpc": "2.0", "id": mid, "result": result}
        except Exception as e:  # never crash the server on one bad request
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32603, "message": str(e)}}

    def serve(self, stdin=None, stdout=None) -> None:
        stdin = stdin or sys.stdin.buffer
        stdout = stdout or sys.stdout.buffer
        for raw in stdin:
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
            else:
                resp = self.handle(msg)
            if resp is not None:
                stdout.write((json.dumps(resp, ensure_ascii=False) + "\n").encode("utf-8"))
                stdout.flush()
