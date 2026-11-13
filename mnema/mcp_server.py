"""MCP server over stdio: lets Claude (Desktop, Code) and other MCP clients use the memory.

JSON-RPC 2.0, one message per line, UTF-8. Standard library only.
Run: python -m mnema mcp --client claude [--vault PATH]
"""

from __future__ import annotations

import json
import sys
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
    "файлы — pc_read_file и pc_write_file, папки — pc_list_dir. Это настоящий доступ, а не описание: когда просят "
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

        if not P.memory_on(self.vault):
            return P.MEMORY_OFF
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
            raise PermissionDenied("доступ к компьютеру выключен владельцем: Настройки → Программа → «Действия на компьютере»")
        from .chat import tools as TL
        from .journal import log_event

        if name in ("pc_run", "pc_write_file") and not c.can_write:
            raise PermissionDenied(f"{c.name} не может менять файлы и запускать команды")
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
        if name == "pc_list_dir":
            p = Path(str(args.get("path") or "~")).expanduser()
            if not p.is_dir():
                raise ValueError("такой папки нет")
            items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))[:300]
            return "\n".join(
                f"{'[папка] ' if x.is_dir() else ''}{x.name}{'' if x.is_dir() else f' · {x.stat().st_size} байт'}"
                for x in items
                if not x.name.startswith(".")
            ) or "(пусто)"
        if name == "pc_write_file":
            p = Path(str(args.get("path") or "")).expanduser()
            if not p.parent.is_dir():
                raise ValueError("такой папки нет")
            text = str(args.get("text") or "")
            # the same write path as the chat: a snapshot and a journal line, so «История» can undo it
            TL._write_bytes(self.vault, self.client_id, p, text.encode("utf-8"), f"записан файл {p.name}")
            return f"Записано: {p} (откат — «Память» → «История»)"
        raise KeyError(name)

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
                    "capabilities": {"tools": {"listChanged": False}},
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
