"""Actions in the chat: the model reads and writes files and memory with the owner's word on every action."""

import os
import sys
import tempfile
import threading
import time
import unittest
import zipfile
from pathlib import Path

os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())

from mnema.agent import profile as P  # noqa: E402
from mnema.chat import engine as CH, providers as PR, tools as TL  # noqa: E402
from mnema.journal import events, undo  # noqa: E402
from mnema.memory import init_vault, remember  # noqa: E402
from mnema.vault import Vault  # noqa: E402
from hidden_topics import lock_cloud  # noqa: E402


def _vault(folder: Path | None = None) -> Vault:
    v = Vault(Path(tempfile.mkdtemp()))
    init_vault(v)
    PR.save(v, "openai", models=["m1"], key="sk-test-0000000000000000")
    P.save(v, {"tools_ask": True})
    if folder:
        P.save(v, {"tool_folders": [str(folder)]})
    return v


class Script:
    """A fake model: each call answers with the next reply; records what it was sent."""

    def __init__(self, *replies):
        self.replies, self.seen = list(replies), []

    def __call__(self, vault, pid, model, system, messages, stop=None, usage=None, meta=None, **kw):
        self.seen.append((system, [dict(m) for m in messages]))
        yield self.replies.pop(0) if self.replies else "Готово."


class Owner:
    """Answers the permission card in a thread, like a click: yes | no | always."""

    def __init__(self, cid_box, choices):
        self.cid_box, self.choices, self.asked = cid_box, list(choices), []
        threading.Thread(target=self.loop, daemon=True).start()

    def loop(self):
        end = time.time() + 20
        while time.time() < end and self.choices:
            for cid, g in list(CH._gen.items()):
                p = g.get("pending")
                if p:
                    self.asked.append(p["what"])
                    CH.answer_action(cid, p["id"], self.choices.pop(0))
            time.sleep(0.05)


class ActionsTest(unittest.TestCase):
    def setUp(self):
        self.old = PR.stream
        self.work = Path(tempfile.mkdtemp())

    def tearDown(self):
        PR.stream = self.old

    def _send(self, v, text, script, choices, cid=""):
        PR.stream = script
        owner = Owner(None, choices)
        r = CH.send(v, text, cid=cid, model="openai:m1", learn=False, sync=True)
        return r, owner

    def test_a_file_is_made_after_yes_and_the_model_goes_on(self):
        v = _vault(self.work)
        target = self.work / "план.md"
        s = Script(f'Сделаю.\n```mnema write_file path="{target}"\n# План\n- шаг один\n```', "Создала план.")
        r, owner = self._send(v, "Сделай план в файле", s, ["yes"])
        self.assertTrue(target.exists())
        self.assertIn("шаг один", target.read_text(encoding="utf-8"))
        self.assertIn("создать файл", owner.asked[0])
        self.assertIn("[Результат действия от Mnemai]", s.seen[1][1][-1]["text"])
        msgs = CH.load_chat(v, r["chat"])["messages"]
        self.assertTrue(any(m.get("kind") == "action" and "Создала файл" in m["text"] for m in msgs))
        self.assertEqual(msgs[-1]["text"], "Создала план.")
        self.assertNotIn("```mnema", "".join(m.get("text", "") for m in msgs))

    def test_the_block_is_never_shown_while_it_streams(self):
        CH._gen["aaaabbbbcccc"] = {
            "text": 'Сделаю.\n```mnema write_file path="x.md"\nтекст',
            "done": False,
            "error": "",
            "phase": "пишу",
            "stop": False,
        }
        self.assertEqual(CH.state("aaaabbbbcccc")["text"], "Сделаю.")

    def test_words_before_the_action_come_first(self):
        v = _vault(self.work)
        target = self.work / "порядок.md"
        s = Script(f'Сделаю.\n```mnema write_file path="{target}"\nтекст\n```', "Готово.")
        r, _ = self._send(v, "Сделай файл", s, ["yes"])
        kinds = [
            (m.get("kind", ""), m.get("text", "")[:7])
            for m in CH.load_chat(v, r["chat"])["messages"]
            if m["role"] == "assistant"
        ]
        self.assertEqual([k for k, _ in kinds], ["", "action", ""])
        self.assertEqual(kinds[0][1], "Сделаю.")

    def test_model_names_read_well(self):
        from mnema.chat.consortium import speaker_name

        self.assertEqual(speaker_name("anthropic:claude-sonnet-4-5"), "Claude Sonnet 4.5")
        self.assertEqual(speaker_name("anthropic:claude-opus-4-1"), "Claude Opus 4.1")

    def test_no_means_nothing_happens(self):
        v = _vault(self.work)
        target = self.work / "не надо.md"
        s = Script(f'```mnema write_file path="{target}"\nтекст\n```', "Хорошо, не делаю.")
        r, _ = self._send(v, "Сделай файл", s, ["no"])
        self.assertFalse(target.exists())
        self.assertIn("не разрешил", s.seen[1][1][-1]["text"])

    def test_yes_for_this_conversation_asks_once(self):
        v = _vault(self.work)
        a, b = self.work / "a.md", self.work / "b.md"
        s = Script(f'```mnema write_file path="{a}"\nА\n```', f'```mnema write_file path="{b}"\nБ\n```', "Оба готовы.")
        r, owner = self._send(v, "Два файла", s, ["always"])
        time.sleep(0.3)
        self.assertTrue(a.exists() and b.exists())
        self.assertEqual(len(owner.asked), 1)

    def test_outside_the_open_folders_is_refused(self):
        v = _vault(self.work)
        elsewhere = Path(tempfile.mkdtemp()) / "x.md"
        with self.assertRaises(TL.Refused):
            TL.resolve(v, str(elsewhere))
        with self.assertRaises(TL.Refused):
            TL.resolve(v, str(v.root / ".mnema" / "token"))

    def test_a_hidden_note_is_read_under_the_rules_of_the_ai(self):
        v = _vault()
        lock_cloud(v)
        remember(v, "MONEYREAD долг 900 тысяч", "card:Деньги #money")
        remember(v, "OPENREAD теннис", "card:Деньги")
        p = v.root / "70 Memory" / "Cards" / "Деньги.md"
        text, _, _ = TL.run(v, {"tool": "read_file", "path": str(p)}, "chatgpt")
        self.assertNotIn("MONEYREAD", text)
        text, _, _ = TL.run(v, {"tool": "read_file", "path": str(p)}, "local")
        self.assertIn("MONEYREAD", text)

    def test_documents_pdf_docx_xlsx(self):
        v = _vault(self.work)
        md = "# Отчёт\n\nИтоги квартала.\n\n| Статья | Сумма |\n|---|---|\n| Аренда | 100000 |\n"
        TL.run(v, {"tool": "make_document", "path": str(self.work / "r.docx"), "body": md})
        with zipfile.ZipFile(self.work / "r.docx") as z:
            self.assertIn("Аренда", z.read("word/document.xml").decode("utf-8"))
        TL.run(v, {"tool": "make_document", "path": str(self.work / "r.xlsx"), "body": md})
        from openpyxl import load_workbook

        ws = load_workbook(self.work / "r.xlsx").active
        self.assertEqual(ws["B2"].value, 100000)
        if TL.edge_exe():
            TL.run(v, {"tool": "make_document", "path": str(self.work / "r.pdf"), "body": md})
            self.assertTrue((self.work / "r.pdf").read_bytes().startswith(b"%PDF"))
        TL.run(v, {"tool": "make_document", "path": str(self.work / "r.docx"), "body": md})
        self.assertTrue((self.work / "r (2).docx").exists())  # never overwrites a document

    def test_every_write_is_undone_from_history(self):
        v = _vault(self.work)
        f = self.work / "заметка.txt"
        f.write_text("было\n", encoding="utf-8")
        TL.run(v, {"tool": "edit_file", "path": str(f), "body": "<<<\nбыло\n===\nстало\n>>>"})
        self.assertIn("стало", f.read_text(encoding="utf-8"))
        undo(v, events(v, 5)[0]["id"])
        self.assertEqual(f.read_text(encoding="utf-8"), "было\n")
        new = self.work / "новый.md"
        TL.run(v, {"tool": "write_file", "path": str(new), "body": "текст"})
        undo(v, events(v, 5)[0]["id"])
        self.assertFalse(new.exists())
        note = v.root / "40 Заметка.md"
        TL.run(v, {"tool": "write_file", "path": str(note), "body": "в памяти"})
        undo(v, events(v, 5)[0]["id"])
        self.assertFalse(note.exists())

    def test_by_default_nothing_is_asked(self):
        v = _vault(self.work)
        P.save(v, {"tools_ask": False})
        target = self.work / "сразу.md"
        s = Script(f'```mnema write_file path="{target}"\nтекст\n```', "Готово.")
        r, owner = self._send(v, "Сделай файл", s, [])
        self.assertTrue(target.exists())
        self.assertEqual(owner.asked, [])
        self.assertFalse(P.DEFAULT["tools_ask"])

    def test_switched_off_means_no_rule_and_no_action(self):
        v = _vault(self.work)
        P.save(v, {"tools": False})
        target = self.work / "x.md"
        s = Script(f'```mnema write_file path="{target}"\nтекст\n```')
        self._send(v, "Сделай файл", s, [])
        self.assertFalse(target.exists())
        self.assertNotIn("Действия на компьютере", s.seen[0][0])


    def test_prompt_tells_the_model_about_the_terminal_only_when_it_is_on(self):
        v = _vault(self.work)
        on = Script("Готово.")
        PR.stream = on
        CH.send(v, "привет", model="openai:m1", learn=False, sync=True)
        self.assertIn("run_command", on.seen[0][0])
        self.assertIn("ЕСТЬ доступ к компьютеру", on.seen[0][0])
        P.save(v, {"pc_access": False})
        off = Script("Готово.")
        PR.stream = off
        CH.send(v, "привет ещё", model="openai:m1", learn=False, sync=True)
        self.assertNotIn("run_command", off.seen[0][0])

    @unittest.skipIf(os.name == "nt", "the checked program is a POSIX shell script")
    def test_open_app_launches_a_program(self):
        v = _vault(self.work)
        marker = self.work / "opened-marker"
        app = self.work / "mnema-test-app"
        app.write_text(f"#!/bin/sh\ntouch '{marker}'\n", encoding="utf-8")
        app.chmod(0o755)
        old = os.environ["PATH"]
        os.environ["PATH"] = str(self.work) + os.pathsep + old
        try:
            text, line, _ = TL.run(v, {"tool": "open_app", "name": "mnema-test-app"})
        finally:
            os.environ["PATH"] = old
        self.assertIn("Открыла программу", text)
        self.assertIn("mnema-test-app", line)
        for _ in range(30):
            if marker.exists():
                break
            time.sleep(0.1)
        self.assertTrue(marker.exists())

    def test_open_app_says_what_is_installed(self):
        v = _vault(self.work)
        with self.assertRaises(TL.Refused):
            TL.run(v, {"tool": "open_app", "name": "definitely-not-installed-app-xyz"})

    def test_terminal_runs_and_the_model_gets_the_output(self):
        v = _vault(self.work)
        s = Script('Проверю систему.\n```mnema run_command command="echo mnema-pc-ok"\n```', 'Команда сработала.')
        r, owner = self._send(v, "Проверь терминал", s, ["yes"])
        self.assertTrue(any("терминал" in w or "команд" in w for w in owner.asked))
        self.assertIn("mnema-pc-ok", str(s.seen[-1][1]))  # the result came back to the model
        msgs = CH.load_chat(v, r["chat"])["messages"]
        self.assertTrue(any(m.get("kind") == "action" and "mnema-pc-ok" in (m.get("text") or "") for m in msgs))
        self.assertTrue(any(e["action"] == "exec" for e in events(v, 30)))  # and it is in the journal

    def test_terminal_can_be_switched_off(self):
        v = _vault(self.work)
        P.save(v, {"pc_access": False})
        s = Script('```mnema run_command command="echo nope"\n```')
        r, owner = self._send(v, "Запусти", s, ["yes"])  # tools_ask is on: answer the card, then it is refused
        msgs = CH.load_chat(v, r["chat"])["messages"]
        self.assertTrue(any("терминал выключен" in (m.get("text") or "") for m in msgs))

    def test_terminal_timeout_stops_the_command(self):
        v = _vault(self.work)
        command = f'"{sys.executable}" -c "import time; time.sleep(3)"'
        s = Script('Проверю таймаут.\n```mnema run_command timeout="1"\n' + command + '\n```', 'Остановила.')
        r, owner = self._send(v, "Запусти долгую команду", s, ["yes"])
        msgs = CH.load_chat(v, r["chat"])["messages"]
        self.assertTrue(any("таймаут" in (m.get("text") or "").lower() for m in msgs))


if __name__ == "__main__":
    unittest.main()
