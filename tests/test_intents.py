"""Short computer commands: one action and one line, without a model round-trip."""

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())

from mnema.agent import profile as P  # noqa: E402
from mnema.chat import engine as CH, intents as IN, providers as PR, tools as TL  # noqa: E402
from mnema.memory import init_vault  # noqa: E402
from mnema.vault import Vault  # noqa: E402


class Intents(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp())
        self.v = Vault(self.work / "vault")
        init_vault(self.v)

    def test_open_commands_are_recognised(self):
        self.assertEqual(IN.fast_open(self.v, "Открой терминал")["name"], "terminal")
        self.assertEqual(IN.fast_open(self.v, "запусти firefox")["name"], "firefox")
        self.assertEqual(IN.fast_open(self.v, "Открой мне хром, пожалуйста")["name"], "chrome")
        self.assertEqual(IN.fast_open(self.v, "open https://example.com")["name"], "https://example.com")
        self.assertIsNone(IN.fast_open(self.v, "расскажи, как прошёл день"))
        self.assertIsNone(IN.fast_open(self.v, "открой файл с отчётом"))

    def test_unknown_program_is_answered_briefly(self):
        answer = IN.answer(self.v, {"tool": "open_app", "name": "definitely-not-installed-app-xyz", "label": "app"})
        self.assertIn("не найдена", answer)
        self.assertLess(len(answer), 400)

    @unittest.skipIf(os.name == "nt", "the checked program is a POSIX shell script")
    def test_send_answers_without_the_model(self):
        marker = self.work / "opened"
        app = self.work / "mnema-test-app"
        app.write_text(f"#!/bin/sh\ntouch '{marker}'\n", encoding="utf-8")
        app.chmod(0o755)
        old_path = os.environ["PATH"]
        os.environ["PATH"] = str(self.work) + os.pathsep + old_path
        old_stream = PR.stream
        PR.stream = lambda *a, **k: (_ for _ in ()).throw(AssertionError("the model must not be called"))
        try:
            r = CH.send(self.v, "Открой mnema-test-app", model="claude_code:sonnet", sync=True, learn=False)
        finally:
            PR.stream = old_stream
            os.environ["PATH"] = old_path
        c = CH.load_chat(self.v, r["chat"])
        self.assertEqual(c["messages"][-1]["role"], "assistant")
        self.assertIn("Готово", c["messages"][-1]["text"])
        for _ in range(30):
            if marker.exists():
                break
            time.sleep(0.1)
        self.assertTrue(marker.exists())


if __name__ == "__main__":
    unittest.main()
