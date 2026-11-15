"""Short computer commands: one action and one line, without a model round-trip."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())

from mnema.chat import engine as CH, intents as IN, providers as PR  # noqa: E402
from mnema.memory import init_vault  # noqa: E402
from mnema.vault import Vault  # noqa: E402

MODELS = ("claude_code:sonnet", "harness:deepseek-flash")


class Intents(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp())
        self.v = Vault(self.work / "vault")
        init_vault(self.v)

    def test_commands_are_recognised(self):
        self.assertEqual(IN.fast_action(self.v, "Открой терминал")["name"], "terminal")
        self.assertEqual(IN.fast_action(self.v, "запусти firefox")["name"], "firefox")
        self.assertEqual(IN.fast_action(self.v, "открой телегу")["name"], "telegram")
        self.assertEqual(IN.fast_action(self.v, "открой фаерфокс")["name"], "firefox")
        self.assertEqual(IN.fast_action(self.v, "Открой мне хром, пожалуйста")["name"], "chrome")
        self.assertEqual(IN.fast_action(self.v, "open https://example.com")["name"], "https://example.com")
        self.assertEqual(
            IN.fast_action(self.v, 'Открой википедию со словом "сон"')["name"],
            "https://ru.wikipedia.org/w/index.php?search=%D1%81%D0%BE%D0%BD",
        )
        self.assertEqual(
            IN.fast_action(self.v, "открой в википедии сон")["name"],
            "https://ru.wikipedia.org/w/index.php?search=%D1%81%D0%BE%D0%BD",
        )
        self.assertEqual(IN.fast_action(self.v, "открой ютуб")["name"], "https://www.youtube.com")
        self.assertIn("search_query=", IN.fast_action(self.v, "открой в ютубе котиков")["name"])
        self.assertEqual(IN.fast_action(self.v, "открой гугл хром")["name"], "chrome")  # the program, not a site
        note = self.v.root / "00 Inbox" / "x.md"
        note.write_text("x", encoding="utf-8")
        self.assertEqual(IN.fast_action(self.v, f"прочитай файл {note}")["tool"], "read_file")
        self.assertEqual(IN.fast_action(self.v, "что в загрузках")["tool"], "list_files")
        self.assertEqual(IN.fast_action(self.v, "найди договор в файлах")["tool"], "find_files")
        self.assertEqual(IN.fast_action(self.v, "выполни echo ok")["tool"], "run_command")
        self.assertEqual(IN.fast_action(self.v, "!echo hi")["tool"], "run_command")
        self.assertEqual(IN.fast_action(self.v, "запомни: я люблю кофе")["tool"], "remember")
        self.assertEqual(IN.fast_action(self.v, "создай файл ~/x.md с текстом: привет")["tool"], "write_file")
        self.assertEqual(IN.fast_action(self.v, "сделай pdf ~/x.pdf из: # План")["tool"], "make_document")
        self.assertEqual(IN.fast_action(self.v, "найди кофе в памяти")["tool"], "memory_find")
        self.assertEqual(IN.fast_action(self.v, "который час")["tool"], "time")
        self.assertEqual(IN.fast_action(self.v, "сколько памяти")["tool"], "system")
        self.assertIsNone(IN.fast_action(self.v, "расскажи, как прошёл день"))
        self.assertIsNone(IN.fast_action(self.v, "Запусти ютуб в терминале"))  # not a shell command: let the model act
        self.assertIsNone(IN.fast_action(self.v, "открой файл с отчётом"))

    def test_file_commands_work_without_a_model(self):
        note = self.v.root / "00 Inbox" / "fast-note.md"
        note.write_text("# Заметка\n\nдоговор с клиентом\n", encoding="utf-8")
        self.assertIn("договор", IN.answer(self.v, IN.fast_action(self.v, f"прочитай файл {note}")))
        listing = IN.answer(self.v, IN.fast_action(self.v, f"что в папке {self.v.root / '00 Inbox'}"))
        self.assertIn("fast-note.md", listing)
        found = IN.answer(self.v, IN.fast_action(self.v, "найди договор в файлах"))
        self.assertIn("fast-note.md", found.lower())
        self.assertEqual(IN.answer(self.v, IN.fast_action(self.v, "запомни: я люблю кофе")), "Запомнила.")
        self.assertIn("я люблю кофе", (self.v.root / "00 Inbox" / "Inbox.md").read_text(encoding="utf-8"))
        self.assertIn("fast-ok", IN.answer(self.v, IN.fast_action(self.v, "выполни echo fast-ok")))
        created = self.v.root / "00 Inbox" / "written.md"
        result = IN.answer(
            self.v, IN.fast_action(self.v, f"создай файл {created} с текстом: привет из быстрой команды")
        )
        self.assertIn("Создала", result)
        self.assertIn("привет из быстрой", created.read_text(encoding="utf-8"))
        from mnema.memory import remember

        remember(self.v, "Пьёт кофе без сахара", "inbox", "owner")
        self.assertIn("кофе", IN.answer(self.v, IN.fast_action(self.v, "найди кофе в памяти")).lower())
        self.assertRegex(IN.answer(self.v, IN.fast_action(self.v, "который час")), r"\d{2}:\d{2}")

    def test_commands_skip_the_learning_model_call(self):
        calls = []
        old_learn, old_stream, old_answer = CH._safe_learn, PR.stream, IN.answer
        CH._safe_learn = lambda *a, **k: calls.append(1)
        PR.stream = lambda *a, **k: (_ for _ in ()).throw(AssertionError("the model must not be called"))
        IN.answer = lambda *a, **k: "Готово — открыла Википедию."
        try:
            r = CH.send(self.v, 'Открой википедию со словом "сон"', model="claude_code:sonnet", sync=True)
            chat = CH.load_chat(self.v, r["chat"])
        finally:
            CH._safe_learn, PR.stream, IN.answer = old_learn, old_stream, old_answer
        self.assertEqual(calls, [], "a command must not go to the learning model")
        self.assertEqual(chat["messages"][-1]["text"], "Готово — открыла Википедию.")

    def test_send_answers_without_the_model_on_every_model(self):
        old_stream = PR.stream
        PR.stream = lambda *a, **k: (_ for _ in ()).throw(AssertionError("the model must not be called"))
        try:
            for model in MODELS:
                r = CH.send(self.v, "выполни echo mnema-fast-ok", model=model, sync=True, learn=False)
                c = CH.load_chat(self.v, r["chat"])
                self.assertEqual(c["messages"][-1]["role"], "assistant")
                self.assertIn("mnema-fast-ok", c["messages"][-1]["text"], model)
        finally:
            PR.stream = old_stream

    def test_install_requests_are_resolved_before_the_model(self):
        import mnema.chat.tools as TL

        with (
            patch.object(TL, "package_manager", lambda: "dnf"),
            patch.object(TL, "resolve_package", lambda pm, term: "aircrack-ng"),
        ):
            call = IN.install_call(self.v, "установи мне aircrack")
            self.assertEqual(call["tool"], "run_command")
            self.assertIn("dnf install -y aircrack-ng", call["command"])
            self.assertEqual(call["packages"], ["aircrack-ng"])
            self.assertEqual(call["timeout"], 900)
            self.assertIsNone(IN.install_call(self.v, "установи программу для wifi"))
            self.assertIsNone(IN.install_call(self.v, "расскажи про aircrack"))
            self.assertIsNone(IN.install_call(self.v, "установи два пакета"))
        with (
            patch.object(TL, "package_manager", lambda: "dnf"),
            patch.object(TL, "resolve_package", lambda pm, term: None),
        ):
            self.assertIsNone(IN.install_call(self.v, "установи airmong"))  # unclear name: the model decides

    def test_installing_a_package_runs_without_a_model(self):
        import mnema.chat.tools as TL

        with (
            patch.object(TL, "package_manager", lambda: "dnf"),
            patch.object(TL, "resolve_package", lambda pm, term: "nmap"),
            patch.object(TL, "install_command", lambda pm, names: "echo mnema-install-ok"),
            patch.object(PR, "stream", side_effect=AssertionError("the model must not be called")),
        ):
            r = CH.send(self.v, "установи nmap", model="claude_code:sonnet", sync=True, learn=False)
        chat = CH.load_chat(self.v, r["chat"])
        text = "\n".join((m.get("text") or "") for m in chat["messages"])
        detail = "\n".join((m.get("detail") or "") for m in chat["messages"])
        self.assertIn("поставила nmap", text)
        self.assertIn("mnema-install-ok", detail)

    def test_a_broken_install_still_ends_the_turn(self):
        import mnema.chat.tools as TL

        with (
            patch.object(TL, "package_manager", lambda: "dnf"),
            patch.object(TL, "resolve_package", lambda pm, term: "nmap"),
            patch.object(TL, "install_command", lambda pm, names: "echo ok"),
            patch.object(CH, "_act", side_effect=RuntimeError("boom")),
        ):
            r = CH.send(self.v, "установи nmap", model="claude_code:sonnet", sync=True, learn=False)
        st = CH.state(r["chat"])
        self.assertTrue(st.get("done"), "the chat must never stay in the «thinking» state")
        chat = CH.load_chat(self.v, r["chat"])
        self.assertTrue(any("Не получилось поставить nmap: boom" in (m.get("text") or "") for m in chat["messages"]))

    def test_a_repeated_stream_chunk_is_kept_once(self):
        class Repeating:
            def __call__(self, *a, **k):
                for _ in range(5):
                    yield "Принял, делаю."

        with patch.object(PR, "stream", Repeating()):
            r = CH.send(self.v, "просто ответь", model="claude_code:sonnet", sync=True, learn=False)
        msgs = CH.load_chat(self.v, r["chat"])["messages"]
        text = [m.get("text") for m in msgs if m.get("role") == "assistant" and m.get("text")][-1]
        self.assertEqual(text, "Принял, делаю.")


if __name__ == "__main__":
    unittest.main()
