"""Short computer commands: one action and one line, without a model round-trip."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
