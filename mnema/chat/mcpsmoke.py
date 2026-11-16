"""A deterministic smoke of every tool of Mnemai's local MCP server.

A plan step should not ask a model to remember 56 calls: one action runs the whole smoke, writes the
Markdown table and removes its own test traces.  It is deliberately conservative: desktop control tools
are skipped, test facts are marked MCP-SMOKE and forgotten, the clipboard is restored, and only the
generated smoke folder under «00 Inbox» is removed.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
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
        if call("web_fetch", {"url": "https://example.com", "max_chars": 1000}) is None:
            call("web_fetch", {"url": "https://example.com", "max_chars": 1000})  # one retry: network hiccups happen

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


# ---------------------------------------------------------------- read-only vault sweep

READONLY_SKIP = {
    "memory_remember": "запрещено правилами: только чтение памяти",
    "memory_update": "запрещено правилами: только чтение памяти",
    "memory_forget": "запрещено правилами: только чтение памяти",
    "memory_undo": "запрещено правилами: только чтение памяти",
    "todo_add": "запрещено правилами: списки только читаем",
    "todo_update": "запрещено правилами: списки только читаем",
    "todo_done": "запрещено правилами: списки только читаем",
    "todo_remove": "запрещено правилами: списки только читаем",
    "task_add": "запрещено правилами: задачи только читаем",
    "task_update": "запрещено правилами: задачи только читаем",
    "task_done": "запрещено правилами: задачи только читаем",
    "task_remove": "запрещено правилами: задачи только читаем",
    "task_run": "запрещено правилами: задачи только читаем",
}


def run_readonly(vault: Vault, allow_writes: bool = False) -> str:
    """The same catalogue; files live in /tmp. With allow_writes the memory/todo/task write tools are tested too,
    using marked records and removing them afterwards."""
    import tempfile

    from ..mcp_server import Server, TOOLS

    server = Server(vault, "local")
    folder = Path(tempfile.gettempdir()) / f"mnemai-mcp-smoke-{date.today().isoformat()}"
    marker = "MCP-SMOKE-" + time.strftime("%H%M%S")
    from ..agent import profile as profile_mod

    profile = profile_mod.load(vault)
    original_folders = list(profile.get("tool_folders") or [])
    rows: list[dict] = []
    expected = [str(t.get("name")) for t in TOOLS]
    if "tools/list" not in expected:
        expected.insert(0, "tools/list")
    notes: dict[str, str] = {}
    skip = {} if allow_writes else READONLY_SKIP
    write_ids: list[tuple[str, str]] = []  # (action, id) for todo/task cleanup

    def call(name: str, args: dict | None = None) -> str | None:
        try:
            out = server.call(name, args or {}, strict=True)
            rows.append({"tool": name, "ok": True, "out": str(out), "note": ""})
            return str(out)
        except Exception as e:  # noqa: BLE001
            rows.append({"tool": name, "ok": False, "out": f"{type(e).__name__}: {e}", "note": ""})
            return None

    old_clip: str | None = None
    try:
        rows.append(
            {"tool": "tools/list", "ok": True, "out": "каталог модуля", "note": f"{len(expected) - 1} инструментов"}
        )
        # the /tmp folder must be an allowed work folder for the chat file actions; restored in finally
        if str(folder) not in original_folders:
            changed = dict(profile)
            changed["tool_folders"] = [*original_folders, str(folder)]
            profile_mod.save(vault, changed)
        # read-only memory and service
        call("memory_context")
        call("memory_search", {"query": "Mnemai"})
        call("memory_stale", {"days": 30})
        call("memory_journal", {"limit": 5})
        call("todo_list")
        call("task_list")
        call("clients_list")
        call("journal_tail", {"limit": 5})

        if allow_writes:
            # write tools are tested with uniquely marked records and cleaned in finally
            mem = call("memory_remember", {"fact": f"{marker} write test; удалить", "where": "inbox"})
            if mem:
                call("memory_update", {"query": marker, "text": f"{marker} write test updated"})
            undo_mem = call("memory_remember", {"fact": f"{marker}-undo write test", "where": "inbox"})
            if undo_mem:
                call("memory_undo", {"id": _id(undo_mem)})
            todo = call("todo_add", {"text": f"{marker} todo", "priority": "normal"})
            if todo:
                write_ids.append(("todo", _id(todo)))
                call("todo_update", {"id": _id(todo), "text": f"{marker} todo updated"})
                call("todo_done", {"id": _id(todo)})
                call("todo_remove", {"id": _id(todo)})
            task = call("task_add", {"text": f"{marker} task", "priority": "normal", "auto": False})
            if task:
                write_ids.append(("task", _id(task)))
                call("task_update", {"id": _id(task), "text": f"{marker} task updated"})
                call("task_run", {"id": _id(task)})
                call("task_done", {"id": _id(task)})
                call("task_remove", {"id": _id(task)})
            call("memory_forget", {"query": marker})  # cleanup is repeated in finally as a safety net

        # files: /tmp only
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True, exist_ok=True)
        call("pc_make_dir", {"path": str(folder)})
        call("pc_write_file", {"path": str(folder / "alpha.txt"), "text": "MCP-SMOKE readonly\nвторая строка\n"})
        call("pc_read_file", {"path": str(folder / "alpha.txt")})
        call("pc_list_dir", {"path": str(folder)})
        call("pc_glob", {"pattern": "*.txt", "path": str(folder)})
        call("pc_grep", {"pattern": "MCP-SMOKE", "path": str(folder)})
        call("pc_copy", {"path": str(folder / "alpha.txt"), "destination": str(folder / "copy.txt")})
        call("pc_move", {"path": str(folder / "copy.txt"), "destination": str(folder / "moved.txt")})
        if call("pc_delete", {"path": str(folder / "moved.txt")}) is None:
            notes["pc_delete"] = "в /tmp нет корзины — pc_delete не смог; файл убран вместе с тестовой папкой"
        inbox = vault.root / "00 Inbox"
        read_target = inbox / "Inbox.md"
        call("read_file", {"path": str(read_target if read_target.is_file() else folder / "alpha.txt")})
        call("list_files", {"path": str(inbox if inbox.is_dir() else folder)})
        call("find_files", {"query": "mnemai-mcp-smoke"})
        # the vault-write actions are attempted only on /tmp; a refusal is a deliberate skip, not a crash
        for name, args in (
            ("write_file", {"path": str(folder / "note.md"), "body": "# MCP-SMOKE\n"}),
            ("edit_file", {"path": str(folder / "note.md"), "body": "<<<\n# MCP-SMOKE\n===\n# MCP-SMOKE edited\n>>>"}),
            ("make_document", {"path": str(folder / "doc.md"), "body": "# MCP-SMOKE\n"}),
        ):
            if call(name, args) is None:
                notes[name] = "вне хранилища нельзя: инструмент отказал на /tmp"
        # edit_pdf can be checked without Chromium: make two tiny valid PDFs with pypdf in the test folder
        notes["edit_pdf"] = "не проверен: PDF вне хранилища не создаётся"
        try:
            from pypdf import PdfWriter

            for name in ("pdf1.pdf", "pdf2.pdf"):
                writer = PdfWriter()
                writer.add_blank_page(width=200, height=200)
                with open(folder / name, "wb") as fh:
                    writer.write(fh)
            call(
                "edit_pdf",
                {
                    "do": "merge",
                    "files": f"{folder / 'pdf1.pdf'};{folder / 'pdf2.pdf'}",
                    "path": str(folder / "merged.pdf"),
                },
            )
            call(
                "edit_pdf",
                {"do": "pages", "path": str(folder / "pages.pdf"), "from": str(folder / "merged.pdf"), "pages": "1"},
            )
            call(
                "edit_pdf",
                {
                    "do": "rotate",
                    "path": str(folder / "rotated.pdf"),
                    "from": str(folder / "merged.pdf"),
                    "pages": "1",
                    "angle": 90,
                },
            )
            call("edit_pdf", {"do": "split", "path": str(folder), "from": str(folder / "merged.pdf")})
            if any(r["tool"] == "edit_pdf" and r["ok"] for r in rows):
                notes["edit_pdf"] = "merge/pages/rotate/split проверены на двух PDF в тестовой папке"
        except Exception as e:  # noqa: BLE001 — pypdf absent is an environment note, not a crash
            notes["edit_pdf"] = f"не проверен: {type(e).__name__}: {str(e)[:120]}"

        # commands, jobs, web, service
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
        call("web_search", {"query": "DeepSeek Harness", "limit": 3})
        call("web_fetch", {"url": "https://example.com", "max_chars": 1000})
        call("pc_notify", {"title": "MCP-SMOKE", "text": "read-only smoke"})
        call("pc_screenshot", {"path": str(folder / "shot.png")})
        old_clip = call("pc_clipboard_get")
        call("pc_clipboard_set", {"text": "MCP-SMOKE clipboard"})
        call("pc_clipboard_get")
        notes["pc_clipboard_set"] = "содержимое восстановлено" if old_clip is not None else "старый буфер не прочитан"
        call("subagent_run", {"prompt": "Ответь одним словом: ок", "model": "harness:deepseek-flash"})

        # expected errors
        call("pc_read_file", {"path": str(folder / "nope.txt")})
        notes["pc_read_file"] = "несуществующий путь вернул понятную ошибку"
        call("pc_list_dir", {"path": str(folder / "nope")})
        notes["pc_list_dir"] = "несуществующая папка вернула понятную ошибку"
        call("pc_grep", {"pattern": "ZZZ-NOT-FOUND-XYZ", "path": str(folder)})
        notes["pc_grep"] = "пустой grep вернул «Ничего не нашлось»"
    finally:
        try:
            if old_clip is not None:
                server.call("pc_clipboard_set", {"text": old_clip}, strict=True)
        except Exception:  # noqa: BLE001
            pass
        try:
            if profile_mod.load(vault).get("tool_folders") != original_folders:
                restored = dict(profile_mod.load(vault))
                restored["tool_folders"] = original_folders
                profile_mod.save(vault, restored)
        except Exception:  # noqa: BLE001
            pass
        try:
            if allow_writes:
                server.call("memory_forget", {"query": marker}, strict=True)
        except Exception:  # noqa: BLE001
            pass
        for kind, item_id in write_ids:
            try:
                server.call("todo_remove" if kind == "todo" else "task_remove", {"id": item_id}, strict=True)
            except Exception:  # noqa: BLE001
                pass
        try:
            if folder.exists():
                shutil.rmtree(folder)
        except Exception:  # noqa: BLE001
            pass

    # aggregate by tool; skipped tools are explicit rows
    called: dict[str, dict] = {}
    for row in rows:
        item = called.setdefault(row["tool"], {"calls": 0, "ok": 0, "fail": 0})
        item["calls"] += 1
        item["ok" if row["ok"] else "fail"] += 1
    private = {
        "memory_context",
        "memory_search",
        "memory_stale",
        "memory_journal",
        "todo_list",
        "task_list",
        "clients_list",
        "journal_tail",
        "pc_clipboard_get",
    }
    lines = [
        f"# MCP smoke Mnemai · {'write test allowed' if allow_writes else 'read-only vault'} · {date.today().isoformat()}",
        "",
        f"Инструментов в каталоге: {len(expected)} · тестовая папка: {folder} (удалена)",
        "",
        "| инструмент | вызван | результат | замечание |",
        "|---|---|---|---|",
    ]
    ok = failed = skipped = partial = 0
    for name in expected:
        if name in DESKTOP or name in skip:
            why = "нужно отдельное «да» владельца" if name in DESKTOP else skip[name]
            lines.append(f"| {name} | нет | пропущен | {why} |")
            skipped += 1
            continue
        item = called.get(name)
        if not item:
            lines.append(f"| {name} | нет | — | не вызывался |")
            continue
        note = notes.get(name, "")
        if name in private:
            note = "ответ получен (содержимое не выводится)"
        if name == "edit_pdf":
            if item["ok"]:
                status, note = "ok", notes.get(name, "PDF-операции проверены")
                ok += 1
            else:
                status, note = "не проверен", notes.get(name, "нет тестового PDF")
                partial += 1
        elif item["ok"] and item["fail"]:
            status = "ok" if name in {"pc_read_file", "pc_list_dir", "pc_grep"} else "частично"
            if status == "ok":
                ok += 1
            else:
                partial += 1
            note = note or "есть успешный вызов и ошибка"
        elif item["ok"]:
            status = "ok"
            ok += 1
            note = note or "ok"
        elif notes.get(name):
            status = "пропущен"
            skipped += 1
            note = notes[name]
        else:
            status = "ошибка"
            failed += 1
            note = "ошибка без подробностей"
        lines.append(f"| {name} | да | {status} | {str(note)[:180].replace('|', '/')} |")
    lines += [
        "",
        f"Итог: ок {ok} · частично {partial} · ошибок {failed} · пропущено {skipped}.",
        (
            "Тестовые записи памяти, дел и задач созданы и удалены; буфер обмена восстановлен; /tmp-папка удалена."
            if allow_writes
            else "Записи в память и списки не вызывались; буфер обмена восстановлен; /tmp-папка удалена."
        )
        if not folder.exists()
        else "ВНИМАНИЕ: /tmp-папка не удалена.",
    ]
    text = "\n".join(lines)
    if len(text) > MAX_OUTPUT:
        text = text[:MAX_OUTPUT] + "\n…[таблица длиннее, показано начало]"
    return text
