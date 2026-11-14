"""Durable tasks: storage, dependencies, and the worker's eligibility rules."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())

from mnema import tasks as T  # noqa: E402
from mnema.memory import init_vault  # noqa: E402
from mnema.vault import Vault  # noqa: E402


class TasksTest(unittest.TestCase):
    def setUp(self):
        self.v = Vault(Path(tempfile.mkdtemp()) / "v")
        init_vault(self.v)

    def test_add_update_dependencies(self):
        a = T.add(self.v, "Первая", priority="high")
        b = T.add(self.v, "Вторая", depends_on=a["id"], auto=True)
        items = T.load(self.v)
        self.assertEqual([x["id"] for x in items], [a["id"], b["id"]])
        self.assertTrue(T.ready(self.v, a, items))
        self.assertFalse(T.ready(self.v, b, items))  # the first one is not done yet
        T.update(self.v, a["id"], status="done")
        items = T.load(self.v)
        self.assertTrue(T.ready(self.v, b, items))
        T.remove(self.v, b["id"])
        self.assertEqual([x["id"] for x in T.load(self.v)], [a["id"]])

    def test_auto_flag_and_model_survive(self):
        t = T.add(self.v, "Фоновая", auto=True, model="harness:deepseek-flash")
        got = T.get(self.v, t["id"])
        self.assertTrue(got["auto"])
        self.assertEqual(got["model"], "harness:deepseek-flash")
        self.assertEqual(got["status"], "open")


if __name__ == "__main__":
    unittest.main()
