"""DeepSeek Harness as the chat brain: offered in the model list, streams its answer, tools shown."""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())

from mnema.chat import providers as PR  # noqa: E402
from mnema.memory import init_vault  # noqa: E402
from mnema.vault import Vault  # noqa: E402

CREDS = Path.home() / ".dsh" / ".credentials.yaml"


def harness_ready() -> bool:
    return bool(PR.dsh_exe()) and CREDS.is_file()


@unittest.skipUnless(harness_ready(), "DeepSeek Harness (dsh + a signed-in account) is not set up here")
class HarnessProvider(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.v = Vault(self.dir)
        init_vault(self.v)

    def test_status_offers_the_harness_model(self):
        st = next(p for p in PR.status(self.v) if p["id"] == "harness")
        self.assertTrue(st["ready"])
        self.assertEqual([m["id"] for m in st["models"]], ["deepseek-flash"])
        self.assertEqual(PR.fetch_models(self.v, "harness"), ["deepseek-flash"])

    def test_stream_answers_and_runs_a_tool(self):
        usage = {}
        pieces = list(
            PR.stream(
                self.v,
                "harness",
                "deepseek-flash",
                "Ты — тестовая модель.",
                [{"role": "user", "text": "Выполни в терминале: echo harness-provider-ok. Ответь только выводом."}],
                usage=usage,
            )
        )
        text = "".join(pieces)
        self.assertIn("harness-provider-ok", text)
        self.assertIn("bash", text)  # the tool call is shown in the conversation
        self.assertGreater(usage.get("in", 0), 0)


if __name__ == "__main__":
    unittest.main()
