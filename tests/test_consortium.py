"""Consortium: several AIs discuss in turn, each sees the others, the last one sums up. Fake models, fake data."""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())

from mnema.chat import consortium as CO, engine as CH, providers as PR  # noqa: E402
from mnema.memory import init_vault  # noqa: E402
from mnema.vault import Vault  # noqa: E402
from test_core import fill  # noqa: E402
from hidden_topics import lock_cloud  # noqa: E402


class Talk:
    def __init__(self):
        self.calls = []

    def __call__(self, vault, pid, model, system, messages, stop=None, usage=None, meta=None):
        if system.startswith("Ты придумываешь"):
            yield "Обсуждение"
            return
        self.calls.append({"pid": pid, "model": model, "system": system, "messages": messages})
        if usage is not None:
            usage.update({"in": 50, "out": 10})
        yield f"Мнение {pid} №{len(self.calls)}"


class TestConsortium(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.v = Vault(self.dir / "v")
        init_vault(self.v)
        fill(self.v)
        self.orig, PR.stream = PR.stream, Talk()
        self.talk = PR.stream

    def tearDown(self):
        PR.stream = self.orig
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_discussion_in_turns_with_summary(self):
        cfg = {"members": ["claude_code:sonnet", "openai:gpt-4o", "gemini:gemini-2.5-pro"], "rounds": 2}
        r = CH.send(self.v, "Стоит ли запускать пилот в ноябре?", model="", sync=True, learn=False, consortium=cfg)
        c = CH.load_chat(self.v, r["chat"])
        ai = [m for m in c["messages"] if m["role"] == "assistant"]
        self.assertEqual(
            [m["speaker"] for m in ai], ["Claude Sonnet", "ChatGPT · gpt-4o", "Gemini · gemini-2.5-pro"] * 2
        )
        self.assertEqual(c["model"], "consortium")
        self.assertTrue(ai[-1].get("summary"))
        self.assertIn("ПОДВОДИШЬ ИТОГ", self.talk.calls[-1]["system"])
        self.assertNotIn("ПОДВОДИШЬ ИТОГ", self.talk.calls[0]["system"])
        # the second speaker hears the first one by name, its own words come back as its turns
        second = self.talk.calls[1]["messages"]
        self.assertIn("Claude Sonnet: Мнение claude_code №1", second[-1]["text"])
        fourth = self.talk.calls[3]["messages"]  # Claude again, round 2
        self.assertEqual([m["role"] for m in fourth], ["user", "assistant", "user"])
        self.assertEqual(fourth[1]["text"], "Мнение claude_code №1")

    def test_speaker_can_use_mnema_tools(self):
        target = self.v.root / "00 Inbox" / "tool-note.md"
        target.write_text("секретное содержимое для спикера", encoding="utf-8")

        class ActionTalk:
            def __init__(self):
                self.calls = 0
                self.systems = []

            def __call__(self, vault, pid, model, system, messages, stop=None, usage=None, meta=None):
                self.calls += 1
                self.systems.append(system)
                if usage is not None:
                    usage.update({"in": 5, "out": 5})
                if self.calls == 1:
                    yield f'Проверю файл.\n```mnema read_file path="{target}"\n```'
                else:
                    yield "Файл прочитан."

        self.talk = ActionTalk()
        PR.stream = self.talk
        cfg = {"members": ["openai:gpt-4o", "gemini:gemini-2.5-pro"], "rounds": 1}
        r = CH.send(self.v, "Проверь файл", sync=True, learn=False, consortium=cfg)
        c = CH.load_chat(self.v, r["chat"])
        actions = [m for m in c["messages"] if m.get("kind") == "action"]
        self.assertEqual(len(actions), 1)
        self.assertIn("tool-note.md", actions[0]["text"])
        self.assertIn("Ты подключён через", self.talk.systems[0])
        self.assertIn("Действия на компьютере", self.talk.systems[0])  # the speaker is told about its tools
        # the second pass saw the file content and answered
        self.assertTrue(
            any("Файл прочитан" in (m.get("text") or "") for m in c["messages"] if m["role"] == "assistant")
        )

    def test_memory_rules_per_participant(self):
        lock_cloud(self.v)
        cfg = {"members": ["claude_code:sonnet", "gemini:gemini-2.5-pro"], "rounds": 1}
        CH.send(self.v, "Привет", sync=True, learn=False, consortium=cfg)
        self.assertIn("Доход 100к", self.talk.calls[0]["system"])  # Claude may see money
        self.assertNotIn("Доход 100к", self.talk.calls[1]["system"])  # Gemini may not

    def test_argue_with_one_answer(self):
        """«Поспорить с разными ИИ»: the author defends its answer, the others question it, a verdict at the end."""
        import time

        r = CH.send(self.v, "Снижать ли цену?", model="openai:gpt-4o", sync=True, learn=False)
        cid = r["chat"]
        answer = [m for m in CH.load_chat(self.v, cid)["messages"] if m["role"] == "assistant"][-1]["text"]
        CO.control(
            self.v,
            cid,
            "start",
            ["openai:gpt-4o", "gemini:gemini-2.5-pro"],
            2,
            extra={
                "format": "debate",
                "challenge": {"by": "openai:gpt-4o", "answer": answer, "question": "Снижать ли цену?"},
            },
        )
        end = time.time() + 15
        while time.time() < end and not CH.state(cid)["done"]:
            time.sleep(0.05)
        cfg = CH.load_chat(self.v, cid)["consortium"]
        self.assertEqual(cfg["challenge"]["by"], "openai:gpt-4o")
        calls = self.talk.calls[1:]  # the first call was the answer itself
        self.assertIn("поспорить с ответом", calls[0]["system"])
        self.assertIn(answer, calls[0]["system"])
        self.assertIn("ЗА", [c for c in calls if c["pid"] == "openai"][0]["system"])
        self.assertIn("ПРОТИВ", [c for c in calls if c["pid"] == "gemini"][0]["system"])

    def test_needs_two(self):
        with self.assertRaises(ValueError):
            CO.clean({"members": ["claude_code:sonnet"]})
        self.assertEqual(
            len(CO.clean({"members": ["claude_code:", "openai:a", "openai:b", "gemini:c", "ollama:d"]})["members"]), 4
        )

    def test_owner_steps_in(self):
        import threading
        import time

        # a speaker in the middle of a sentence finishes it
        g = {"done": False, "stop": False, "text": "Я думаю, что"}
        threading.Thread(target=lambda: (time.sleep(0.3), g.update(done=True))).start()
        CO.wait_stopped(g, timeout=5)
        self.assertTrue(g["stop"] and g["done"])
        # one that has said nothing yet (a slow or hung service) is dropped at once
        g = {"done": False, "stop": False, "text": ""}
        t0 = time.time()
        CO.wait_stopped(g, timeout=5)
        self.assertTrue(g["stop"] and g["abandoned"])
        self.assertLess(time.time() - t0, 0.5)


if __name__ == "__main__":
    unittest.main()
