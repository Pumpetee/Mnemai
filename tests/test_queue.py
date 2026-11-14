"""Messages written while an answer is being written: accepted, queued, and drained after a turn (or a crash)."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())

from mnema.chat import engine as CH  # noqa: E402
from mnema.memory import init_vault  # noqa: E402
from mnema.vault import Vault  # noqa: E402


class QueueTest(unittest.TestCase):
    def setUp(self):
        self.v = Vault(Path(tempfile.mkdtemp()) / "v")
        init_vault(self.v)
        self.cid = "aaaabbbbcccc"
        CH.save_chat(
            self.v,
            {"id": self.cid, "title": "t", "model": "openai:gpt-4o", "created": CH._now(), "messages": []},
        )
        CH._gen[self.cid] = {"done": False, "stop": False}
        CH._queued.pop(self.cid, None)

    def tearDown(self):
        CH._gen.pop(self.cid, None)
        CH._queued.pop(self.cid, None)

    def test_a_message_during_work_is_accepted_and_queued(self):
        r = CH.send(self.v, "поправка: сначала сделай Y", cid=self.cid, sync=False)
        self.assertTrue(r.get("queued"))
        self.assertEqual(CH._queued[self.cid][0]["text"], "поправка: сначала сделай Y")
        self.assertTrue(CH.load_chat(self.v, self.cid)["messages"][-1].get("queue"))

    def test_stop_with_a_instruction_is_queued(self):
        r = CH.send(self.v, "Стоп. Ответь одним словом: ок", cid=self.cid, sync=False)
        self.assertTrue(r.get("queued"))
        self.assertEqual(CH._queued[self.cid][0]["text"], "Стоп. Ответь одним словом: ок")

    def test_stop_does_not_create_a_queued_task(self):
        r = CH.send(self.v, "стоп", cid=self.cid, sync=False)
        self.assertTrue(r.get("stopped"))
        self.assertNotIn(self.cid, CH._queued)

    def test_drain_keeps_going_after_a_failed_task(self):
        CH._queued[self.cid] = [{"text": "one"}, {"text": "two"}]
        calls = []

        def fake_send(*a, **k):
            calls.append(k.get("cid"))
            if len(calls) == 1:
                raise RuntimeError("boom")
            return {"chat": self.cid}

        old = CH.send
        CH.send = fake_send
        try:
            CH._drain_queue(self.v, self.cid)
        finally:
            CH.send = old
        self.assertEqual(calls, [self.cid, self.cid])  # the failed one is reported, the next one still starts
        self.assertNotIn(self.cid, CH._queued)
        self.assertTrue(
            any("следующую задачу" in (m.get("error") or "") for m in CH.load_chat(self.v, self.cid)["messages"])
        )


if __name__ == "__main__":
    unittest.main()
