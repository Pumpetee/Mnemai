"""MCP server over stdio: lets Claude (Desktop, Code) and other MCP clients use the memory.

JSON-RPC 2.0, one message per line, UTF-8. Standard library only.
Run: python -m mnema mcp --client claude [--vault PATH]
"""

from __future__ import annotations

import json
import os
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import time
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
    "pc_delete; поиск в интернете — web_search и web_fetch; фоновые задачи — pc_job_start/output/kill/list; "
    "список дел — todo_*; долговечные задачи — task_*; другой ИИ — subagent_run; поиск файлов — pc_glob и pc_grep; "
    "уведомление — pc_notify, снимок экрана — pc_screenshot; управление — pc_clipboard_*/pc_click/pc_type/pc_key/pc_scroll. "
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
        "name": "pc_job_start",
        "description": "Запустить команду в фоне (не блокирует). Возвращает id для pc_job_output/pc_job_kill.",
        "inputSchema": {
            "type": "object",
            "properties": {"command": {"type": "string"}, "cwd": {"type": "string"}},
            "required": ["command"],
        },
    },
    {
        "name": "pc_job_output",
        "description": "Вывод фоновой задачи по id; если она завершилась — и код возврата.",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string"}, "tail": {"type": "integer", "minimum": 200, "maximum": 50000}},
            "required": ["id"],
        },
    },
    {
        "name": "pc_job_kill",
        "description": "Остановить фоновую задачу по id.",
        "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
    },
    {
        "name": "pc_job_list",
        "description": "Список фоновых задач: что ещё идёт и чем закончилось.",
        "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer", "default": 20}}},
    },
    {
        "name": "pc_glob",
        "description": "Найти файлы по glob-шаблону (например **/*.py) на компьютере.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string"},
                "limit": {"type": "integer", "default": 100},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "pc_grep",
        "description": "Найти регулярное выражение в текстовых файлах на компьютере (путь, строка, текст).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string"},
                "glob": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "todo_add",
        "description": "Добавить задачу в список дел (priority: normal | high | low).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "normal", "high"]},
            },
            "required": ["text"],
        },
    },
    {
        "name": "todo_list",
        "description": "Показать список дел (status: open | done | all).",
        "inputSchema": {
            "type": "object",
            "properties": {"status": {"type": "string", "enum": ["open", "done", "all"]}},
        },
    },
    {
        "name": "todo_done",
        "description": "Отметить задачу выполненной по id.",
        "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
    },
    {
        "name": "todo_update",
        "description": "Изменить текст или приоритет задачи по id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "text": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "normal", "high"]},
            },
            "required": ["id"],
        },
    },
    {
        "name": "todo_remove",
        "description": "Удалить задачу из списка по id.",
        "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
    },
    {
        "name": "task_add",
        "description": "Добавить долговечную задачу (переживает перезапуск). priority: low | normal | high; depends_on — id задачи.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "normal", "high"]},
                "depends_on": {"type": "string"},
                "auto": {"type": "boolean", "description": "Выполнять автоматически фоновым worker'ом."},
                "model": {"type": "string", "description": "provider:model для выполнения; по умолчанию модель Mnema."},
            },
            "required": ["text"],
        },
    },
    {
        "name": "task_list",
        "description": "Список долговечных задач (open | done | all).",
        "inputSchema": {
            "type": "object",
            "properties": {"status": {"type": "string", "enum": ["open", "done", "all"]}},
        },
    },
    {
        "name": "task_update",
        "description": "Изменить задачу: текст, приоритет или статус (open | done | cancelled).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "text": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "normal", "high"]},
                "status": {"type": "string", "enum": ["open", "done", "cancelled"]},
            },
            "required": ["id"],
        },
    },
    {
        "name": "task_done",
        "description": "Отметить долговечную задачу выполненной.",
        "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
    },
    {
        "name": "task_remove",
        "description": "Удалить задачу из долговечного списка.",
        "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
    },
    {
        "name": "task_run",
        "description": "Выполнить задачу из реестра сейчас (моделью Mnema) и отметить результат.",
        "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
    },
    {
        "name": "subagent_run",
        "description": "Поручить отдельный вопрос другому ИИ (model: провайдер:модель, по умолчанию — текущая модель "
        "Mnema). Субагент отвечает текстом, без инструментов.",
        "inputSchema": {
            "type": "object",
            "properties": {"prompt": {"type": "string"}, "model": {"type": "string"}},
            "required": ["prompt"],
        },
    },
    {
        "name": "pc_clipboard_get",
        "description": "Прочитать системный буфер обмена.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "pc_clipboard_set",
        "description": "Положить текст в системный буфер обмена.",
        "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
    },
    {
        "name": "pc_click",
        "description": "Клик мышью по координатам экрана (нужен ydotool/wtype/xdotool).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "button": {"type": "integer", "minimum": 1, "maximum": 3, "default": 1},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "pc_type",
        "description": "Напечатать текст в активное окно (нужен ydotool/wtype/xdotool).",
        "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
    },
    {
        "name": "pc_key",
        "description": "Нажать клавишу/комбинацию (например Return, ctrl+c) — нужен ydotool/wtype/xdotool.",
        "inputSchema": {"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]},
    },
    {
        "name": "pc_scroll",
        "description": "Прокрутить колесо: положительное — вверх, отрицательное — вниз.",
        "inputSchema": {"type": "object", "properties": {"amount": {"type": "integer"}}, "required": ["amount"]},
    },
    {
        "name": "clients_list",
        "description": "Кто из ассистентов подключён и какие права у него есть.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "journal_tail",
        "description": "Последние действия в журнале Mnema (кто что сделал), с учётом прав этого ассистента.",
        "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer", "default": 30}}},
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
PC_WRITE = {
    "pc_run",
    "pc_write_file",
    "pc_open_app",
    "pc_make_dir",
    "pc_move",
    "pc_copy",
    "pc_delete",
    "pc_screenshot",
    "pc_job_start",
    "pc_job_kill",
    "pc_clipboard_set",
    "pc_click",
    "pc_type",
    "pc_key",
    "pc_scroll",
}
TODO_WRITE = {"todo_add", "todo_done", "todo_update", "todo_remove"}
TASK_WRITE = {"task_add", "task_update", "task_done", "task_remove", "task_run"}
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
        if name in TASK_WRITE and not c.can_write:
            raise PermissionDenied(f"{c.name} не может менять задачи")
        if name.startswith("task_"):
            return self._task(name, args)
        if name == "subagent_run":
            return self._subagent(args)
        if name == "clients_list":
            from .clients import load_clients

            return "\n".join(
                f"- {cl.id}: {cl.name} · {'вкл' if cl.enabled else 'выкл'} · {'пишет' if cl.can_write else 'только читает'} · "
                f"сферы: {', '.join(cl.scopes)}"
                for cl in load_clients(self.vault).values()
            )
        if name == "journal_tail":
            c2 = get_client(self.vault, self.client_id)
            limit = max(1, min(200, int(args.get("limit") or 30)))
            rows = []
            for e in events(self.vault, 500):
                if not self._may_see(e, c2):
                    continue
                rows.append(f"{e['ts']} · {e['client']} · {e['action']} · {e['summary']}")
                if len(rows) >= limit:
                    break
            return "\n".join(rows) or "Журнал пуст."
        if name in TODO_WRITE and not c.can_write:
            raise PermissionDenied(f"{c.name} не может менять список дел")
        if name.startswith("todo_"):
            return self._todo(name, args)
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
        if name == "pc_clipboard_get":
            from . import osapi as OS

            return OS.clipboard_get() or "(буфер пуст)"
        if name == "pc_clipboard_set":
            from . import osapi as OS

            ok = OS.clipboard_set(str(args.get("text") or ""))
            if ok:
                log_event(self.vault, self.client_id, "write", "буфер обмена")
            return "Записано в буфер." if ok else "Не получилось записать в буфер."
        if name == "pc_click":
            from . import osapi as OS

            if not OS.click(int(args.get("x") or 0), int(args.get("y") or 0), int(args.get("button") or 1)):
                raise ValueError("нет средства управления мышью: нужен ydotool/wtype (Wayland) или xdotool (X11)")
            log_event(self.vault, self.client_id, "exec", "клик мышью")
            return "Клик."
        if name == "pc_type":
            from . import osapi as OS

            if not OS.type_text(str(args.get("text") or "")):
                raise ValueError("нет средства ввода: нужен ydotool/wtype (Wayland) или xdotool (X11)")
            log_event(self.vault, self.client_id, "exec", "ввод с клавиатуры")
            return "Напечатано."
        if name == "pc_key":
            from . import osapi as OS

            if not OS.key(str(args.get("key") or "")):
                raise ValueError("нет средства ввода: нужен ydotool/wtype (Wayland) или xdotool (X11)")
            log_event(self.vault, self.client_id, "exec", f"клавиша {args.get('key')}")
            return "Нажато."
        if name == "pc_scroll":
            from . import osapi as OS

            if not OS.scroll(int(args.get("amount") or 0)):
                raise ValueError("нет средства управления мышью: нужен ydotool/wtype (Wayland) или xdotool (X11)")
            return "Прокручено."
        if name == "pc_job_start":
            return self._job_start(args)
        if name == "pc_job_output":
            return self._job_output(args)
        if name == "pc_job_kill":
            return self._job_kill(args)
        if name == "pc_job_list":
            return self._job_list(args)
        if name == "pc_glob":
            return self._glob(args)
        if name == "pc_grep":
            return self._grep(args)
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

    def _jobs_root(self) -> Path:
        home = Path(os.environ.get("MNEMA_HOME") or (Path.home() / ".mnema"))
        p = home / "jobs"
        p.mkdir(mode=0o700, parents=True, exist_ok=True)
        return p

    def _job_meta(self, jid: str) -> tuple[Path, dict] | None:
        jid = re.sub(r"[^0-9a-f]", "", str(jid))[:16]
        if not jid:
            return None
        d = self._jobs_root() / jid
        try:
            meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return d, meta

    def _job_start(self, args: dict) -> str:
        command = str(args.get("command") or "").strip()
        if not command:
            raise ValueError("нужна команда")
        work = Path(str(args.get("cwd") or "~")).expanduser()
        if not work.is_dir():
            raise ValueError("такой папки нет")
        jid = secrets.token_hex(4)
        d = self._jobs_root() / jid
        d.mkdir(mode=0o700, parents=True, exist_ok=True)
        log, code = d / "output.log", d / "exit-code"
        script = d / ("run.cmd" if os.name == "nt" else "run.sh")
        if os.name == "nt":
            script.write_text(
                "@echo off\r\n(" + command + ") > " + str(log) + " 2>&1\r\necho %ERRORLEVEL% > " + str(code) + "\r\n",
                encoding="utf-8",
            )
            argv = ["cmd", "/c", str(script)]
        else:
            script.write_text(
                "#!/bin/bash\n("
                + command
                + ") > "
                + shlex.quote(str(log))
                + " 2>&1\nprintf '%s\\n' $? > "
                + shlex.quote(str(code))
                + "\n",
                encoding="utf-8",
            )
            script.chmod(0o700)
            argv = ["/bin/bash" if Path("/bin/bash").exists() else "/bin/sh", str(script)]
        proc = subprocess.Popen(
            argv,
            cwd=str(work),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        meta = {
            "id": jid,
            "command": command,
            "cwd": str(work),
            "pid": proc.pid,
            "started": time.time(),
        }
        (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        log_event(self.vault, self.client_id, "exec", f"фоновая задача {jid}: {command[:160]}")
        return f"Запущено в фоне: id {jid} · {command[:120]}\nВывод: pc_job_output id={jid} · остановить: pc_job_kill id={jid}"

    def _job_output(self, args: dict) -> str:
        found = self._job_meta(str(args.get("id") or ""))
        if not found:
            raise ValueError("такой фоновой задачи нет")
        d, meta = found
        limit = max(200, min(50000, int(args.get("tail") or 4000)))
        try:
            raw = (d / "output.log").read_text(encoding="utf-8", errors="replace")
        except OSError:
            raw = ""
        code = None
        try:
            code = int((d / "exit-code").read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            pass
        head = f"[задача {meta['id']} · {'завершена, код ' + str(code) if code is not None else 'выполняется'}]"
        return head + "\n" + (raw[-limit:].strip() or "(вывода пока нет)")

    def _job_kill(self, args: dict) -> str:
        found = self._job_meta(str(args.get("id") or ""))
        if not found:
            raise ValueError("такой фоновой задачи нет")
        d, meta = found
        pid = int(meta.get("pid") or 0)
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True, timeout=15)
            else:
                os.killpg(pid, 15)
        except (OSError, ProcessLookupError):
            pass
        (d / "exit-code").write_text("143\n", encoding="utf-8")
        log_event(self.vault, self.client_id, "exec", f"остановлена фоновая задача {meta['id']}")
        return f"Задача {meta['id']} остановлена."

    def _job_list(self, args: dict) -> str:
        limit = max(1, min(100, int(args.get("limit") or 20)))
        rows = []
        for d in sorted(self._jobs_root().iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if not d.is_dir():
                continue
            meta: dict = {}
            try:
                meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
                code = int((d / "exit-code").read_text(encoding="utf-8").strip())
            except (OSError, ValueError):
                code = None
            rows.append(
                f"{meta.get('id', d.name)} · {'готово' if code is not None else 'идёт'} · "
                f"{meta.get('command', '')[:100]}"
            )
            if len(rows) >= limit:
                break
        return "\n".join(rows) or "Фоновых задач нет."

    def _glob(self, args: dict) -> str:
        pattern = str(args.get("pattern") or "").strip()
        if not pattern:
            raise ValueError("нужен pattern")
        root = Path(str(args.get("path") or "~")).expanduser()
        if not root.is_dir():
            raise ValueError("такой папки нет")
        limit = max(1, min(1000, int(args.get("limit") or 100)))
        try:
            hits = list(root.glob(pattern))
        except (OSError, ValueError) as e:
            raise ValueError(f"плохой шаблон: {e}") from e
        log_event(self.vault, self.client_id, "read", f"glob {pattern} в {root}", [])
        return "\n".join(str(p) for p in hits[:limit]) or "Ничего не нашлось."

    def _grep(self, args: dict) -> str:
        pattern = str(args.get("pattern") or "")
        if not pattern:
            raise ValueError("нужен pattern")
        try:
            rx = re.compile(pattern)
        except re.error as e:
            raise ValueError(f"плохая регулярка: {e}") from e
        root = Path(str(args.get("path") or "~")).expanduser()
        if not root.is_dir():
            raise ValueError("такой папки нет")
        globpat = str(args.get("glob") or "*")
        limit = max(1, min(200, int(args.get("limit") or 50)))
        skip = {".git", "node_modules", ".cache", ".venv", "target", "dist", "__pycache__"}
        out: list[str] = []
        started = time.time()
        for p in root.rglob(globpat):
            if time.time() - started > 15 or len(out) >= limit:
                break
            if not p.is_file() or any(part in skip for part in p.parts):
                continue
            try:
                if p.stat().st_size > 2_000_000:
                    continue
                data = p.read_bytes()
                if b"\x00" in data[:4096]:
                    continue
                text = data.decode("utf-8", "replace")
            except OSError:
                continue
            for n, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    out.append(f"{p}:{n}: {line[:300]}")
                    if len(out) >= limit:
                        break
        log_event(self.vault, self.client_id, "read", f"grep {pattern} в {root}", [])
        return "\n".join(out) or "Ничего не нашлось."

    def _todo_path(self) -> Path:
        self.vault.service.mkdir(parents=True, exist_ok=True)
        return self.vault.service / "todo.json"

    def _todo_read(self) -> list[dict]:
        try:
            data = json.loads(self._todo_path().read_text(encoding="utf-8"))
            return [x for x in data if isinstance(x, dict)]
        except (OSError, ValueError):
            return []

    def _todo_write(self, items: list[dict]) -> None:
        self._todo_path().write_text(json.dumps(items[:500], ensure_ascii=False, indent=1), encoding="utf-8")

    def _todo(self, name: str, args: dict) -> str:
        items = self._todo_read()
        if name == "todo_add":
            text = " ".join(str(args.get("text") or "").split())
            if not text:
                raise ValueError("нужен текст задачи")
            item = {
                "id": secrets.token_hex(4),
                "text": text,
                "priority": args.get("priority") if args.get("priority") in ("low", "normal", "high") else "normal",
                "done": False,
                "created": time.time(),
            }
            items.append(item)
            self._todo_write(items)
            log_event(self.vault, self.client_id, "write", f"задача: {text[:160]}")
            return f"Задача добавлена: id {item['id']} · {text}"
        if name == "todo_list":
            status = str(args.get("status") or "open")
            show = items if status == "all" else [x for x in items if bool(x.get("done")) == (status == "done")]
            show.sort(key=lambda x: (bool(x.get("done")), x.get("priority") != "high", -float(x.get("created") or 0)))
            return (
                "\n".join(
                    f"{'[x]' if x.get('done') else '[ ]'} {x.get('id')} · {x.get('priority', 'normal')} · {x.get('text')}"
                    for x in show[:100]
                )
                or "Список дел пуст."
            )
        if name == "task_run":
            from . import tasks as T

            return T.run(self.vault, str(args.get("id") or ""), self.client_id)
        found = next((x for x in items if x.get("id") == str(args.get("id") or "")), None)
        if not found:
            raise ValueError("такой задачи нет")
        if name == "todo_done":
            found["done"] = True
        elif name == "todo_update":
            if str(args.get("text") or "").strip():
                found["text"] = " ".join(str(args["text"]).split())
            if args.get("priority") in ("low", "normal", "high"):
                found["priority"] = args["priority"]
        elif name == "todo_remove":
            items.remove(found)
        self._todo_write(items)
        log_event(self.vault, self.client_id, "write", f"список дел: {name} {found.get('id')}")
        return f"Готово: {name} {found.get('id')}"

    def _tasks_path(self) -> Path:
        self.vault.service.mkdir(parents=True, exist_ok=True)
        return self.vault.service / "tasks.json"

    def _tasks(self) -> list[dict]:
        try:
            data = json.loads(self._tasks_path().read_text(encoding="utf-8"))
            return [x for x in data if isinstance(x, dict)]
        except (OSError, ValueError):
            return []

    def _tasks_write(self, items: list[dict]) -> None:
        self._tasks_path().write_text(json.dumps(items[:1000], ensure_ascii=False, indent=1), encoding="utf-8")

    def _task(self, name: str, args: dict) -> str:
        items = self._tasks()
        if name == "task_add":
            text = " ".join(str(args.get("text") or "").split())
            if not text:
                raise ValueError("нужен текст задачи")
            depends = str(args.get("depends_on") or "").strip()
            if depends and not any(x.get("id") == depends for x in items):
                raise ValueError("зависимость не найдена")
            item = {
                "id": secrets.token_hex(4),
                "text": text,
                "priority": args.get("priority") if args.get("priority") in ("low", "normal", "high") else "normal",
                "status": "open",
                "depends_on": depends,
                "auto": bool(args.get("auto")),
                "model": str(args.get("model") or ""),
                "created": time.time(),
                "updated": time.time(),
                "attempts": 0,
                "error": "",
            }
            items.append(item)
            self._tasks_write(items)
            log_event(self.vault, self.client_id, "write", f"задача: {text[:160]}")
            return f"Задача добавлена: id {item['id']} · {text}"
        if name == "task_list":
            status = str(args.get("status") or "open")
            show = items if status == "all" else [x for x in items if x.get("status") == status]
            show.sort(key=lambda x: (x.get("priority") != "high", -float(x.get("created") or 0)))
            return (
                "\n".join(
                    f"[{x.get('status')}] {x.get('id')} · {x.get('priority')} · {x.get('text')}"
                    + (f" (ждёт {x['depends_on']})" if x.get("depends_on") else "")
                    for x in show[:200]
                )
                or "Задач нет."
            )
        found = next((x for x in items if x.get("id") == str(args.get("id") or "")), None)
        if not found:
            raise ValueError("такой задачи нет")
        if name == "task_done":
            found["status"] = "done"
        elif name == "task_update":
            if str(args.get("text") or "").strip():
                found["text"] = " ".join(str(args["text"]).split())
            if args.get("priority") in ("low", "normal", "high"):
                found["priority"] = args["priority"]
            if args.get("status") in ("open", "done", "cancelled"):
                found["status"] = args["status"]
        elif name == "task_remove":
            items.remove(found)
        found["updated"] = time.time()
        self._tasks_write(items)
        log_event(self.vault, self.client_id, "write", f"задача: {name} {found.get('id')}")
        return f"Готово: {name} {found.get('id')}"

    def _subagent(self, args: dict) -> str:
        prompt = str(args.get("prompt") or "").strip()
        if not prompt:
            raise ValueError("нужен prompt")
        from .agent import profile as P
        from .chat import engine as CH, providers as PR

        model = str(args.get("model") or "").strip() or CH.default_model(self.vault)
        if not model:
            raise ValueError("нет доступной модели: выбери модель в Настройки → ИИ и модели")
        pid, mname = CH.split_model(model)
        if not any(p["id"] == pid and p["ready"] for p in PR.status(self.vault)):
            raise ValueError(f"{pid} не подключён")
        system = CH.system_prompt(self.vault, pid, log=False, query=prompt, model=mname)
        if not P.memory_on(self.vault):
            system += "\n\nПамять выключена владельцем."
        usage: dict = {}
        text = PR.complete(
            self.vault,
            pid,
            mname,
            system,
            [{"role": "user", "text": prompt}],
            usage=usage,
            meta={"purpose": "mcp subagent", "client": self.client_id},
        )
        return text.strip() or "(субагент ничего не ответил)"

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
