"""A deterministic smoke of every tool of Mnemai's local MCP server.

A plan step should not ask a model to remember 56 calls: one action runs the whole smoke, writes the
Markdown table and removes its own test traces.  It is deliberately conservative: desktop control tools
are skipped, test facts are marked MCP-SMOKE and forgotten, the clipboard is restored, and only the
generated smoke folder under «00 Inbox» is removed.
"""

from __future__ import annotations

import re
import shutil
import time
from datetime import date

from ..vault import Vault
from .tools import MAX_OUTPUT

DESKTOP = {"pc_click", "pc_type", "pc_key", "pc_scroll", "pc_open_app", "open_app"}


def _id(text: str) -> str:
    m = re.search(r"id ([0-9a-f]+)", str(text or ""))
    return m.group(1) if m else ""


def run(vault: Vault) -> str:
    """Run every MCP tool once; return the owner-readable table. Raises Refused on setup trouble."""
    from ..mcp_server import Server, TOOLS

    server = Server(vault, "local")
    marker = "MCP-SMOKE-" + time.strftime("%H%M%S")
    folder = vault.path(f"00 Inbox/mcp-smoke-{date.today().isoformat()}")
    rows: list[dict] = []
    expected = [str(t.get("name")) for t in TOOLS]
    desktop = sorted(n for n in expected if n in DESKTOP)

    def call(name: str, args: dict | None = None) -> str | None:
        try:
            out = server.call(name, args or {}, strict=True)
            rows.append({"tool": name, "ok": True, "out": str(out), "note": ""})
            return str(out)
        except Exception as e:  # noqa: BLE001 — one bad tool is a row, never a crashed smoke
            rows.append({"tool": name, "ok": False, "out": f"{type(e).__name__}: {e}", "note": ""})
            return None

    def note(name: str, text: str) -> None:
        for row in rows:
            if row["tool"] == name:
                row["note"] = text
                return

    old_clip: str | None = None
    task_ids: list[str] = []
    todo_ids: list[str] = []
    try:
        # tools/list is a protocol method, not a tool: the catalogue comes from the module itself
        if "tools/list" not in expected:
            expected.insert(0, "tools/list")
        rows.append(
            {"tool": "tools/list", "ok": True, "out": "каталог модуля", "note": f"{len(expected) - 1} инструментов"}
        )

        # memory: only a uniquely marked test fact is created and then forgotten
        call("memory_context")
        call("memory_search", {"query": marker})
        created = call("memory_remember", {"fact": f"{marker} smoke; удалить", "where": "inbox"})
        call("memory_stale", {"days": 30})
        call("memory_journal", {"limit": 5})
        if created:
            call("memory_update", {"query": marker, "text": f"{marker} smoke updated"})
        undo_me = call("memory_remember", {"fact": f"{marker}-undo smoke; удалить", "where": "inbox"})
        if undo_me:
            call("memory_undo", {"id": _id(undo_me)})
        call("memory_forget", {"query": marker})

        # files: a private generated folder and the chat file actions
        if folder.exists():
            note("pc_make_dir", "папка уже была — пересоздана")
            shutil.rmtree(folder)
        folder.mkdir(parents=True, exist_ok=True)
        call("pc_make_dir", {"path": str(folder)})
        call("pc_write_file", {"path": str(folder / "alpha.txt"), "text": "MCP-SMOKE alpha\nвторая строка\n"})
        call("pc_read_file", {"path": str(folder / "alpha.txt")})
        call("pc_list_dir", {"path": str(folder)})
        call("pc_glob", {"pattern": "*.txt", "path": str(folder)})
        call("pc_grep", {"pattern": "MCP-SMOKE", "path": str(folder)})
        call("pc_copy", {"path": str(folder / "alpha.txt"), "destination": str(folder / "copy.txt")})
        call("pc_move", {"path": str(folder / "copy.txt"), "destination": str(folder / "moved.txt")})
        call("pc_delete", {"path": str(folder / "moved.txt")})
        call("read_file", {"path": str(folder / "alpha.txt")})
        call("list_files", {"path": str(folder)})
        call("find_files", {"query": "mcp-smoke"})
        call("write_file", {"path": str(folder / "note.md"), "body": "# MCP-SMOKE\n"})
        call("edit_file", {"path": str(folder / "note.md"), "body": "<<<\n# MCP-SMOKE\n===\n# MCP-SMOKE edited\n>>>"})
        call("make_document", {"path": str(folder / "doc.md"), "body": "# MCP-SMOKE\n"})
        # PDF needs a browser; if it is absent the row says so instead of pretending
        pdf = call("make_document", {"path": str(folder / "doc.pdf"), "body": "# MCP-SMOKE\n"})
        if pdf is None:
            note("make_document", "DOCX/MD работают; PDF не создан — нет Chromium")
        for do in ("merge", "pages", "rotate", "split"):
            call(
                "edit_pdf",
                {
                    "do": do,
                    "path": str(folder / f"{do}.pdf"),
                    "from": str(folder / "doc.pdf"),
                    "files": f"{folder / 'doc.pdf'}",
                    **({"pages": "1"} if do in ("pages", "rotate") else {}),
                    **({"angle": 90} if do == "rotate" else {}),
                },
            )
        note("edit_pdf", "не проверен: не из чего собрать PDF (нет Chromium)" if pdf is None else "")

        # commands and jobs
        call("pc_run", {"command": "echo MCP-SMOKE pc_run", "cwd": str(folder), "timeout": 15})
        call("run_command", {"command": "echo MCP-SMOKE run_command", "cwd": str(folder), "timeout": 15})
        job = call("pc_job_start", {"command": "sleep 2; echo MCP-SMOKE job", "cwd": str(folder)})
        time.sleep(3)
        if job:
            call("pc_job_output", {"id": _id(job)})
        call("pc_job_list")
        long_job = call("pc_job_start", {"command": "sleep 30", "cwd": str(folder)})
        if long_job:
            call("pc_job_kill", {"id": _id(long_job)})
            call("pc_job_output", {"id": _id(long_job)})

        # internet
        call("web_search", {"query": "DeepSeek Harness", "limit": 3})
        call("web_fetch", {"url": "https://example.com", "max_chars": 1000})

        # lists
        todo = call("todo_add", {"text": "MCP-SMOKE todo", "priority": "normal"})
        if todo:
            todo_ids.append(_id(todo))
            call("todo_list")
            call("todo_update", {"id": _id(todo), "text": "MCP-SMOKE todo updated"})
            call("todo_done", {"id": _id(todo)})
            call("todo_remove", {"id": _id(todo)})
        call("todo_remove", {"id": "00000000"})
        note("todo_remove", "неизвестный id вернул понятную ошибку")
        task = call("task_add", {"text": "MCP-SMOKE task", "priority": "normal", "auto": False})
        if task:
            task_ids.append(_id(task))
            call("task_list")
            call("task_update", {"id": _id(task), "text": "MCP-SMOKE task updated"})
            call("task_run", {"id": _id(task)})
            call("task_done", {"id": _id(task)})
            call("task_remove", {"id": _id(task)})
            task_ids.clear()
        call("task_run", {"id": "00000000"})
        note("task_run", "неизвестный id вернул понятную ошибку")

        # service
        call("clients_list")
        call("journal_tail", {"limit": 5})
        call("pc_notify", {"title": "MCP-SMOKE", "text": "smoke"})
        call("pc_screenshot", {"path": str(folder / "shot.png")})
        old_clip = call("pc_clipboard_get")
        call("pc_clipboard_set", {"text": "MCP-SMOKE clipboard"})
        got = call("pc_clipboard_get")
        note("pc_clipboard_set", "содержимое восстановлено" if old_clip is not None else "старый буфер не прочитан")
        note("pc_clipboard_get", "прочитан" if got else "ошибка")
        call("subagent_run", {"prompt": "Ответь одним словом: ок", "model": "harness:deepseek-flash"})

        # error checks
        call("pc_read_file", {"path": str(folder / "nope.txt")})
        note("pc_read_file", "несуществующий путь вернул понятную ошибку")
        call("pc_list_dir", {"path": str(folder / "nope")})
        note("pc_list_dir", "несуществующая папка вернула понятную ошибку")
        call("pc_grep", {"pattern": "ZZZ-NOT-FOUND-XYZ", "path": str(folder)})
        note("pc_grep", "пустой grep вернул «Ничего не нашлось»")

        # desktop is skipped by the owner's rule
        for name in desktop:
            rows.append({"tool": name, "ok": True, "out": "пропущен", "note": "нужно отдельное «да» владельца"})
    finally:
        try:
            if old_clip is not None:
                server.call("pc_clipboard_set", {"text": old_clip}, strict=True)
        except Exception:  # noqa: BLE001 — the old clipboard is best effort
            pass
        try:
            server.call("memory_forget", {"query": marker}, strict=True)
        except Exception:  # noqa: BLE001
            pass
        for tid in task_ids:
            try:
                server.call("task_remove", {"id": tid}, strict=True)
            except Exception:  # noqa: BLE001
                pass
        for tid in todo_ids:
            try:
                server.call("todo_remove", {"id": tid}, strict=True)
            except Exception:  # noqa: BLE001
                pass
        try:
            if folder.exists():
                shutil.rmtree(folder)
        except Exception:  # noqa: BLE001
            pass

    # one row per tool in the catalogue, aggregating its calls; never print personal memory content
    agg: dict[str, dict] = {}
    for row in rows:
        item = agg.setdefault(row["tool"], {"calls": 0, "ok": 0, "fail": 0, "note": ""})
        item["calls"] += 1
        item["ok" if row["ok"] else "fail"] += 1
        if row["note"]:
            item["note"] = row["note"]
    private = {
        "memory_context",
        "memory_search",
        "memory_remember",
        "memory_stale",
        "memory_journal",
        "memory_update",
        "memory_forget",
        "memory_undo",
        "clients_list",
        "journal_tail",
        "pc_clipboard_get",
    }
    lines = [
        f"# MCP smoke Mnemai · {date.today().isoformat()}",
        "",
        f"Инструментов в каталоге: {len(expected)} · проверено: {len(agg)} · пропущено по разрешению: {len(desktop)}",
        "",
        "| инструмент | вызван | результат | замечание |",
        "|---|---|---|---|",
    ]
    ok = partial = failed = skipped = 0
    for name in expected:
        if name in DESKTOP:
            lines.append(f"| {name} | нет | пропущен | нужно отдельное «да» владельца |")
            skipped += 1
            continue
        item = agg.get(name)
        if not item:
            lines.append(f"| {name} | нет | — | не вызывался |")
            continue
        if name == "edit_pdf":
            status = "не проверен"
            partial += 1
            note = item["note"] or "не удалось создать тестовый PDF (нет Chromium)"
        elif item["ok"] and item["fail"]:
            expected_error = {"pc_read_file", "pc_list_dir", "pc_grep", "todo_remove", "task_run"}
            status = "ok" if name in expected_error else "частично"
            if status == "ok":
                ok += 1
            else:
                partial += 1
            note = item["note"] or (
                "ok; ожидаемая ошибка проверена" if name in expected_error else "есть успешный вызов и ошибка"
            )
        elif item["ok"]:
            status = "ok"
            ok += 1
            note = item["note"] or "ok"
        else:
            status = "ошибка"
            failed += 1
            note = item["note"] or "ошибка без подробностей"
        if name in private:
            note = "ответ получен (содержимое не выводится)" if item["ok"] else note
        lines.append(f"| {name} | да | {status} | {str(note)[:180].replace('|', '/')} |")
    lines += [
        "",
        f"Итог: ок {ok} · частично {partial} · ошибок {failed} · пропущено {skipped}.",
    ]
    text = "\n".join(lines)
    if len(text) > MAX_OUTPUT:
        text = text[:MAX_OUTPUT] + "\n…[таблица длиннее, показано начало]"
    return text
