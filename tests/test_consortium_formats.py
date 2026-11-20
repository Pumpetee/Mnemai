"""Consortium settings: format of the discussion, roles, who sums up, length of turns. Fake models."""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())

from mnema.chat import consortium as CO, engine as CH, providers as PR  # noqa: E402
from mnema.memory import init_vault  # noqa: E402
from mnema.vault import Vault  # noqa: E402
from test_consortium_table import Talk  # noqa: E402

M3 = ["claude_code:sonnet", "claude_code:opus", "claude_code:haiku"]


class Formats(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.v = Vault(self.dir / "v")
        init_vault(self.v)
        self.orig, PR.stream = PR.stream, Talk()
        self.talk = PR.stream

    def tearDown(self):
        PR.stream = self.orig
        shutil.rmtree(self.dir, ignore_errors=True)

    def ai(self, cid):
        return [m for m in CH.load_chat(self.v, cid)["messages"] if m["role"] == "assistant" and not m.get("kind")]

    def test_clean_keeps_only_valid_settings(self):
        c = CO.clean(
            {
                "members": M3,
                "rounds": 2,
                "format": "debate",
                "roles": {M3[0]: "skeptic", "x:y": "lawyer", M3[1]: "nope"},
                "summarizer": M3[0],
                "length": "short",
            }
        )
        self.assertEqual(
            (c["format"], c["roles"], c["summarizer"], c["length"]), ("debate", {M3[0]: "skeptic"}, M3[0], "short")
        )
        c = CO.clean({"members": M3, "format": "chaos", "summarizer": "x:y", "length": "huge"})
        self.assertEqual((c["format"], c["summarizer"], c["length"]), ("council", "", "normal"))

    def test_stages_per_format(self):
        self.assertEqual([CO.stage_of(r, 3, "debate") for r in range(3)], ["pos", "rebut", "verdict"])
        self.assertEqual([CO.stage_of(r, 3, "brainstorm") for r in range(3)], ["ideas", "grow", "best"])
        self.assertEqual([CO.stage_of(r, 2, "redteam") for r in range(2)], ["attack", "risks"])
        self.assertEqual([CO.stage_of(r, 3) for r in range(3)], ["own", "check", "final"])

    def test_debate_roles_summarizer_and_length_reach_the_models(self):
        cfg = {
            "members": M3,
            "rounds": 2,
            "format": "debate",
            "roles": {M3[1]: "finance"},
            "summarizer": M3[0],
            "length": "short",
        }
        r = CH.send(self.v, "Открывать ли офис в Казани?", sync=True, learn=False, consortium=cfg)
        calls = self.talk.calls
        self.assertEqual(len(calls), 6)
        self.assertIn("Круг «Позиции»", calls[0]["system"])
        self.assertIn("Твоя сторона в дебатах: ЗА", calls[0]["system"])
        self.assertIn("Твоя сторона в дебатах: ПРОТИВ", calls[1]["system"])
        # the roles are fixed by the owner's decision: the first member leads, the rest participate (a role the
        # owner picked earlier no longer changes the discussion), the chosen summarizer sums up in the last round
        self.assertIn("Ты — ведущий", calls[0]["system"])
        self.assertIn("Ты — участник", calls[1]["system"])
        self.assertNotIn("Финансист", calls[1]["system"])
        self.assertIn("Ты — суммаризатор", calls[5]["system"])
        self.assertIn("Не больше 80 слов", calls[0]["system"])
        self.assertEqual([c["model"] for c in calls[3:]], ["opus", "haiku", "sonnet"])  # the summarizer speaks last
        self.assertIn("ТЫ ПОДВОДИШЬ ИТОГ", calls[5]["system"])
        self.assertIn("Не больше 120 слов", calls[5]["system"])
        last = self.ai(r["chat"])[-1]
        self.assertTrue(last.get("summary"))
        self.assertEqual(self.ai(r["chat"])[3]["stage"], "Вердикт")


if __name__ == "__main__":
    unittest.main()
