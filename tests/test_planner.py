"""The task constructor: three plans with executors, estimates, and a chain that passes work between AIs."""

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())

from mnema.chat import engine as CH, planner as PL, providers as PR  # noqa: E402
from mnema.memory import init_vault  # noqa: E402
from mnema.vault import Vault  # noqa: E402

STATUS = [
    {"id": "local", "name": "На этом компьютере", "ready": True, "models": [{"id": "qwen3", "name": "Qwen3 8B"}]},
    {
        "id": "harness",
        "name": "DeepSeek",
        "ready": True,
        "models": [{"id": "deepseek-flash", "name": "DeepSeek Flash"}],
    },
    {"id": "claude_code", "name": "Claude", "ready": True, "models": [{"id": "haiku", "name": "Claude Haiku"}]},
    {"id": "openai", "name": "ChatGPT", "ready": False, "models": [{"id": "gpt-6", "name": "GPT-6"}]},
]


def _vault() -> Vault:
    v = Vault(Path(tempfile.mkdtemp()))
    init_vault(v)
    return v


class Planner(unittest.TestCase):
    def test_every_plan_has_executors_and_estimates(self):
        v = _vault()
        with patch.object(PR, "status", lambda vault: STATUS):
            plans = PL.fallback_plans(v, "Сделай отчёт по договорам")
        self.assertEqual([p["id"] for p in plans], ["fast", "optimal", "quality"])
        allowed = {"local:qwen3", "harness:deepseek-flash", "claude_code:haiku"}
        for plan in plans:
            self.assertTrue(plan["steps"])
            for step in plan["steps"]:
                self.assertIn(step["model"], allowed)
                self.assertGreater(step["est"]["tokens"], 0)
                self.assertGreater(step["est"]["seconds"], 0)
                self.assertLessEqual(step["est"]["tokens_min"], step["est"]["tokens"])
                self.assertGreaterEqual(step["est"]["tokens_max"], step["est"]["tokens"])
                self.assertLessEqual(step["est"]["seconds_min"], step["est"]["seconds"])
                self.assertGreaterEqual(step["est"]["seconds_max"], step["est"]["seconds"])
            self.assertGreater(plan["estimate"]["tokens"], 0)
            self.assertGreater(plan["estimate"]["seconds"], 0)
            self.assertLessEqual(plan["estimate"]["tokens_min"], plan["estimate"]["tokens"])
            self.assertGreaterEqual(plan["estimate"]["tokens_max"], plan["estimate"]["tokens"])
            self.assertLessEqual(plan["estimate"]["seconds_min"], plan["estimate"]["seconds"])
            self.assertGreaterEqual(plan["estimate"]["seconds_max"], plan["estimate"]["seconds"])
            self.assertLessEqual(plan["estimate"]["cost_min"], plan["estimate"]["cost"])
            self.assertGreaterEqual(plan["estimate"]["cost_max"], plan["estimate"]["cost"])
            self.assertTrue(plan["why"])  # the difference is explained, not just priced
        self.assertGreater(len(plans[2]["steps"]), len(plans[0]["steps"]))  # «качественно» длиннее «быстро»

    def test_propose_falls_back_when_the_planner_model_fails(self):
        v = _vault()
        with (
            patch.object(PR, "status", lambda vault: STATUS),
            patch.object(PR, "complete", side_effect=RuntimeError("нет сети")),
        ):
            plans = PL.propose(v, "Напиши письмо клиенту")
        self.assertEqual(len(plans), 3)
        self.assertEqual(plans[0]["id"], "fast")

    def test_propose_gives_the_planner_memory_and_history(self):
        v = _vault()
        with (
            patch.object(PR, "status", lambda vault: STATUS),
            patch.object(PL, "_memory", lambda vault, pid: "ПАМЯТЬ: владелец на Fedora"),
            patch.object(PL, "_history", lambda vault, cid: ["Владелец: мы делаем Mnemai"]),
            patch.object(PR, "complete", side_effect=RuntimeError("нет сети")),
        ):
            plans = PL.propose(v, "Обнови план", "abcdef123456")
        self.assertTrue(all(p["context"]["memory_chars"] > 0 for p in plans))
        self.assertEqual(plans[0]["context"]["history_msgs"], 1)
        doc = plans[0].get("doc")
        self.assertTrue(doc and Path(doc).is_file())  # the schema is also a Markdown document
        self.assertIn("Схема задачи", Path(doc).read_text(encoding="utf-8"))

    def test_models_table_has_prices_and_kinds(self):
        v = _vault()
        with patch.object(PR, "status", lambda vault: STATUS):
            rows = PL.models_table(v)
        by = {r["model"]: r for r in rows}
        self.assertIn("local:qwen3", by)
        self.assertEqual(by["local:qwen3"]["price_in"], 0)
        self.assertEqual(by["local:qwen3"]["price_out"], 0)
        self.assertGreater(by["harness:deepseek-flash"]["price_in"], 0)
        self.assertGreaterEqual(by["harness:deepseek-flash"]["tier"], 1)

    def test_the_owner_can_choose_who_picks_the_executors(self):
        v = _vault()

        def run_with(planner):
            with (
                patch.object(PR, "status", lambda vault: STATUS),
                patch.object(PL, "_memory", lambda vault, pid: ""),
                patch.object(PL, "_history", lambda vault, cid: []),
                patch.object(PR, "complete", side_effect=RuntimeError("нет сети")),
            ):
                return PL.propose(v, "Сделай отчёт", "", planner)

        self.assertEqual(run_with("local")[0]["planner"]["model"], "local:qwen3")
        self.assertEqual(run_with("strong")[0]["planner"]["model"], "claude_code:haiku")
        self.assertEqual(run_with("medium")[0]["planner"]["model"], "harness:deepseek-flash")  # tier 2
        self.assertEqual(run_with("harness:deepseek-flash")[0]["planner"]["model"], "harness:deepseek-flash")
        with patch.object(PR, "status", lambda vault: STATUS):
            with self.assertRaises(ValueError):
                PL.propose(v, "Сделай отчёт", "", "no-such:model")

    def test_the_chain_passes_work_from_one_ai_to_the_next(self):
        v = _vault()
        chat = {
            "id": "abcdef123456",
            "title": "План",
            "created": CH._now(),
            "session": CH.current_session(v)["id"],
            "messages": [],
        }
        CH.save_chat(v, chat)
        plan = {
            "id": "optimal",
            "title": "Оптимально",
            "note": "",
            "task": "Сделай отчёт",
            "steps": [
                {
                    "role": "План",
                    "instruction": "Составь план",
                    "out": "план",
                    "model": "harness:deepseek-flash",
                    "model_name": "DeepSeek Flash",
                    "provider": "DeepSeek",
                },
                {
                    "role": "Финал",
                    "instruction": "Сделай отчёт",
                    "out": "финал",
                    "model": "claude_code:haiku",
                    "model_name": "Claude Haiku",
                    "provider": "Claude",
                },
            ],
        }
        calls = []

        def fake_complete(vault, pid, model, system, messages, usage=None, meta=None):
            calls.append((pid, model, messages[0]["text"]))
            return f"результат шага {len(calls)}"

        with (
            patch.object(PR, "status", lambda vault: STATUS),
            patch.object(PR, "complete", fake_complete),
            patch.object(CH, "_drain_queue") as drain,
        ):
            PL.run(v, chat["id"], plan)
            for _ in range(100):
                if CH._gen[chat["id"]]["done"]:
                    break
                time.sleep(0.05)
        drain.assert_called_once()  # a correction typed during the chain starts the next turn
        self.assertEqual([c[0] for c in calls], ["harness", "claude_code"])
        self.assertIn("результат шага 1", calls[1][2])  # the second AI sees the first answer
        msgs = CH.load_chat(v, chat["id"])["messages"]
        self.assertTrue(any(m.get("kind") == "plan" for m in msgs))
        ready = next(m for m in msgs if m.get("kind") == "plan")
        self.assertEqual(ready["plan"]["status"], "done")
        self.assertEqual(ready["plan"]["steps"][0]["output"], "результат шага 1")
        self.assertEqual(ready["plan"]["steps"][1]["output"], "результат шага 2")
        result = next(m for m in msgs if m.get("kind") == "plan_result")
        self.assertEqual(result["text"], "результат шага 2")  # the answer is the final step, not a wall of text

    def test_no_connected_models_is_explained(self):
        v = _vault()
        with patch.object(PR, "status", lambda vault: []):
            with self.assertRaises(ValueError) as ctx:
                PL.fallback_plans(v, "что угодно")
        self.assertIn("модел", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
