"""Engine settings: modes, sliders, monthly limit. Fake data only."""

import datetime as dt
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mnema import tuning  # noqa: E402
from mnema.chat import engine as CH  # noqa: E402
from mnema.learn import settings as S  # noqa: E402
from mnema.memory import init_vault  # noqa: E402
from mnema.vault import Vault  # noqa: E402


class TestTuning(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.v = Vault(self.dir)
        init_vault(self.v)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_default_is_balance(self):
        e = tuning.get(self.v)
        self.assertEqual((e["mode"], e["memory"], e["answer"]), ("balance", 4200, 3000))

    def test_mode_sets_everything_and_learning_follows(self):
        e = tuning.save(self.v, {"mode": "eco"})
        self.assertEqual((e["precise"], e["memory"], e["answer"], e["ctx"], e["learn"]), (1, 3000, 1000, 4096, 120))
        self.assertEqual(S.load(self.v)["interval_minutes"], 120)

    def test_slider_makes_custom_and_keeps_the_rest(self):
        e = tuning.save(self.v, {"mode": "max"})
        self.assertEqual((e["precise"], e["economy"]), (4, False))  # the most precise step sends whole
        e = tuning.save(self.v, {"precise": 3})
        self.assertEqual(
            (e["mode"], e["memory"], e["docs"], e["economy"], e["answer"]), ("custom", 8000, 12000, True, 8000)
        )
        e = tuning.save(self.v, {"answer": 99999, "precise": 9})  # clipped to the limits
        self.assertEqual((e["precise"], e["answer"]), (4, 16000))

    def test_reset_to_defaults_keeps_memory_and_keys(self):
        from mnema import api_chat
        from mnema.agent import profile as P

        tuning.save(self.v, {"precise": 0, "month": 5000})
        P.save(
            self.v,
            {"scribe_mode": "quality", "tools_ask": True, "tool_folders": ["C:/work"], "extra_folders": ["D:/n"]},
        )
        code, _ = api_chat.post(self.v, "/api/settings/reset", {})
        self.assertEqual(code, 200)
        e, p = tuning.get(self.v), P.load(self.v)
        self.assertEqual((e["mode"], e["precise"], e["month"]), ("balance", 2, 0))
        self.assertEqual((p["scribe_mode"], p["tools_ask"]), ("quality", False))
        self.assertEqual((p["tool_folders"], p["extra_folders"]), (["C:/work"], ["D:/n"]))  # folders stay

    def test_old_settings_pick_the_nearest_step(self):
        from mnema.agent import profile as P

        P.save(self.v, {"engine": {"mode": "custom", "memory": 7000}})
        self.assertEqual(tuning.get(self.v)["precise"], 3)
        P.save(self.v, {"engine": {"mode": "balance"}, "economy": False})  # «economy off» before 1.4
        self.assertEqual((tuning.get(self.v)["precise"], tuning.get(self.v)["economy"]), (4, False))

    def test_month_usage_and_limit_only_for_cloud(self):
        month = dt.date.today().strftime("%Y-%m")
        CH.save_chat(
            self.v,
            {
                "id": "aaaaaaaaaaaa",
                "title": "t",
                "created": f"{month}-01T10:00:00",
                "model": "openai:gpt-4o",
                "messages": [
                    {"role": "user", "text": "q", "ts": f"{month}-01T10:00:00"},
                    {
                        "role": "assistant",
                        "text": "a",
                        "ts": f"{month}-01T10:00:05",
                        "model": "openai:gpt-4o",
                        "tokens": {"in": 900, "out": 200},
                    },
                    {
                        "role": "assistant",
                        "text": "b",
                        "ts": f"{month}-01T10:01:00",
                        "model": "local:gemma-3-4b",
                        "tokens": {"in": 500, "out": 100},
                    },
                    {
                        "role": "assistant",
                        "text": "c",
                        "ts": "2020-01-01T10:00:00",
                        "model": "openai:gpt-4o",
                        "tokens": {"in": 5000, "out": 5000},
                    },
                ],
            },
        )
        u = tuning.month_usage(self.v)
        self.assertEqual((u["cloud"], u["local"], u["by"]), (1100, 600, {"openai": 1100}))
        tuning.save(self.v, {"month": 1000})
        with self.assertRaises(ValueError):
            tuning.check_month(self.v, "openai")
        tuning.check_month(self.v, "local")  # the local model is never limited
        with self.assertRaises(ValueError):
            CH.send(self.v, "привет", model="openai:gpt-4o", sync=True)


if __name__ == "__main__":
    unittest.main()
