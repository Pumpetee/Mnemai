"""The task constructor: three plans with executors, estimates, and a chain that passes work between AIs."""

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())

from mnema.chat import engine as CH, planner as PL, providers as PR, tools as TL  # noqa: E402
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


def _chat(v: Vault) -> dict:
    chat = {
        "id": "abcdef123456",
        "title": "План",
        "created": CH._now(),
        "session": CH.current_session(v)["id"],
        "messages": [],
    }
    CH.save_chat(v, chat)
    return chat


def _schema_doc(v: Vault, task: str) -> str:
    """A real schema document in the vault: the plan result appends its report to it."""
    folder = v.root / "00 Inbox" / "Схемы"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "plan.md"
    path.write_text(f"# Схема задачи\n\n**Задача:** {task}\n", encoding="utf-8")
    return str(path)


def _plan(v: Vault, task: str, steps: list[tuple[str, str, str, str]], doc: bool = True) -> dict:
    """A ready-to-run plan; every step is (model, model_name, role, instruction)."""
    plan = {"id": "optimal", "title": "Оптимально", "note": "", "task": task, "steps": []}
    for model, model_name, role, instruction in steps:
        plan["steps"].append(
            {
                "role": role,
                "instruction": instruction,
                "out": "ответ",
                "model": model,
                "model_name": model_name,
                "provider": model_name,
            }
        )
    if doc:
        plan["doc"] = _schema_doc(v, task)
    return plan


def _wait(chat_id: str, tries: int = 200) -> None:
    for _ in range(tries):
        if (CH._gen.get(chat_id) or {}).get("done"):
            return
        time.sleep(0.02)
    raise AssertionError("план не завершился за отведённое время")


def _messages(v: Vault, chat_id: str) -> list[dict]:
    return CH.load_chat(v, chat_id)["messages"]


class Planner(unittest.TestCase):
    def test_readonly_plan_document_detection(self):
        self.assertTrue(PL._is_mcp_readonly_sweep("Проверь все инструменты MCP: хранилище только читаем, tools/list"))
        self.assertFalse(PL._is_mcp_readonly_sweep("Проверь все инструменты MCP, tools/list"))

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

        def fake_complete(vault, pid, model, system, messages, usage=None, meta=None, stop=None):
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
        for step in ready["plan"]["steps"]:
            self.assertEqual(step["status"], "ok")
            self.assertEqual(step["actions"], 0)
            self.assertEqual(step["note"], "")
        self.assertNotIn("stop_reason", ready["plan"])  # a finished chain has nothing to stop
        self.assertEqual(result["plan"]["task"], "Сделай отчёт")
        self.assertIsNone(result["plan"]["stop_reason"])

    def test_no_connected_models_is_explained(self):
        v = _vault()
        with patch.object(PR, "status", lambda vault: []):
            with self.assertRaises(ValueError) as ctx:
                PL.fallback_plans(v, "что угодно")
        self.assertIn("модел", str(ctx.exception))

    def test_empty_step_stops_the_plan_and_says_why(self):
        v = _vault()
        chat = _chat(v)
        plan = _plan(
            v,
            "Сделай отчёт",
            [
                ("harness:deepseek-flash", "DeepSeek Flash", "План", "Составь план отчёта"),
                ("claude_code:haiku", "Claude Haiku", "Финал", "Собери отчёт"),
            ],
        )
        calls = []

        def fake_complete(vault, pid, model, system, messages, usage=None, meta=None, stop=None):
            calls.append(pid)
            return ""

        with (
            patch.object(PR, "status", lambda vault: STATUS),
            patch.object(PR, "complete", fake_complete),
            patch.object(CH, "_drain_queue"),
        ):
            PL.run(v, chat["id"], plan)
            _wait(chat["id"])

        messages = _messages(v, chat["id"])
        ready = next(m for m in messages if m.get("kind") == "plan")["plan"]
        result = next(m for m in messages if m.get("kind") == "plan_result")
        self.assertEqual(len(calls), 2)  # two honest attempts of step 1, no call for step 2
        self.assertEqual(ready["status"], "stopped")
        self.assertEqual(ready["stop_reason"], "empty_step")
        self.assertEqual(ready["steps"][0]["status"], "empty")
        self.assertEqual(ready["steps"][0]["actions"], 0)
        self.assertTrue(ready["steps"][0]["note"])
        self.assertEqual(ready["steps"][1]["status"], "stopped")  # the rest is not run
        self.assertIn("не выполнялся", ready["steps"][1]["note"])
        self.assertIn("шаге 1 из 2", result["text"])
        self.assertIn("План", result["text"])  # the role is named
        self.assertIn("модель не вызвала инструменты", result["text"])
        self.assertFalse(result["text"].startswith("_"))  # no literal markdown underscores in the owner's chat
        self.assertIn("Открой документ", result["text"])
        self.assertIn("пересобери схему", result["text"])
        self.assertNotIn("Шаг не дал текста", result["text"])  # a bare complaint is never enough
        self.assertEqual(result["plan"]["task"], "Сделай отчёт")
        self.assertEqual(result["plan"]["stop_reason"], "empty_step")
        doc = Path(plan["doc"]).read_text(encoding="utf-8")
        self.assertIn("**Задача:** Сделай отчёт", doc)
        self.assertIn("empty_step", doc)
        self.assertIn("статус: empty", doc)
        self.assertIn("действий: 0", doc)
        self.assertIn("**Что случилось:**", doc)

    def test_tool_using_empty_step_gets_one_summary_call_without_tools(self):
        v = _vault()
        chat = _chat(v)
        plan = _plan(
            v, "Прочитай заметки", [("harness:deepseek-flash", "DeepSeek Flash", "Чтение", "Прочитай документ")]
        )
        calls = []

        def fake_complete(vault, pid, model, system, messages, usage=None, meta=None, stop=None):
            calls.append({"system": system, "messages": messages})
            if len(calls) == 1:
                return "```mnema read_file path=notes.md```"
            if len(calls) == 2:
                return ""
            return "Итог: в документе пять пунктов."

        def fake_parse(text):
            if "mnema" in text:
                return {"tool": "read_file", "path": "notes.md", "start": 0, "end": len(text)}
            return None

        with (
            patch.object(PR, "status", lambda vault: STATUS),
            patch.object(PR, "complete", fake_complete),
            patch.object(TL, "enabled", lambda vault: True),
            patch.object(TL, "rule", lambda vault, small=False: "ПРАВИЛО ИНСТРУМЕНТОВ"),
            patch.object(TL, "parse", fake_parse),
            patch.object(TL, "before", lambda text, call: ""),
            patch.object(CH, "_act", lambda *args, **kwargs: "документ прочитан"),
            patch.object(CH, "_drain_queue"),
        ):
            PL.run(v, chat["id"], plan)
            _wait(chat["id"])

        self.assertEqual(len(calls), 3)  # the action call, the empty answer, and ONE summary call
        self.assertEqual(calls[-1]["messages"][-1]["text"], PL.SUMMARY_ASK)
        self.assertIn("Инструменты", calls[-1]["messages"][-1]["text"])
        self.assertIn(PL.TOOLS_FORBIDDEN, calls[-1]["system"])
        messages = _messages(v, chat["id"])
        ready = next(m for m in messages if m.get("kind") == "plan")["plan"]
        result = next(m for m in messages if m.get("kind") == "plan_result")
        self.assertEqual(ready["status"], "done")
        self.assertEqual(ready["steps"][0]["status"], "ok")
        self.assertEqual(ready["steps"][0]["actions"], 1)
        self.assertEqual(ready["steps"][0]["output"], "Итог: в документе пять пунктов.")
        self.assertEqual(result["text"], "Итог: в документе пять пунктов.")
        self.assertIsNone(result["plan"]["stop_reason"])

    def test_a_repeated_action_stops_a_looping_plan(self):
        v = _vault()
        chat = _chat(v)
        plan = _plan(
            v, "Проверь MCP", [("harness:deepseek-flash", "DeepSeek Flash", "Проверка", "Вызови clients_list")]
        )
        calls = []

        def fake_complete(vault, pid, model, system, messages, usage=None, meta=None, stop=None):
            calls.append(1)
            return '```mnema mcp_call name="clients_list"\n{}\n```'

        def fake_parse(text):
            return {"tool": "mcp_call", "name": "clients_list", "args": {}, "start": 0, "end": len(text)}

        with (
            patch.object(PR, "status", lambda vault: STATUS),
            patch.object(PR, "complete", fake_complete),
            patch.object(TL, "enabled", lambda vault: True),
            patch.object(TL, "rule", lambda vault, small=False: "ПРАВИЛО ИНСТРУМЕНТОВ"),
            patch.object(TL, "parse", fake_parse),
            patch.object(TL, "before", lambda text, call: ""),
            patch.object(CH, "_act", lambda *args, **kwargs: "список клиентов"),
            patch.object(CH, "_drain_queue"),
        ):
            PL.run(v, chat["id"], plan)
            _wait(chat["id"])

        self.assertEqual(len(calls), 3)  # the same action three times is a loop, not work
        messages = _messages(v, chat["id"])
        ready = next(m for m in messages if m.get("kind") == "plan")["plan"]
        result = next(m for m in messages if m.get("kind") == "plan_result")
        self.assertEqual(ready["status"], "stopped")
        self.assertEqual(ready["stop_reason"], "loop")
        self.assertEqual(ready["steps"][0]["status"], "stopped")
        self.assertIn("три раза", result["text"])
        self.assertEqual(result["plan"]["stop_reason"], "loop")

    def test_owner_stop_is_reported_as_such(self):
        v = _vault()
        chat = _chat(v)
        plan = _plan(
            v,
            "Сделай отчёт",
            [
                ("harness:deepseek-flash", "DeepSeek Flash", "План", "Составь план"),
                ("claude_code:haiku", "Claude Haiku", "Финал", "Собери отчёт"),
            ],
        )

        def fake_complete(vault, pid, model, system, messages, usage=None, meta=None, stop=None):
            CH._gen[chat["id"]]["stop"] = True  # the owner pressed Escape while the step was running
            return ""

        with (
            patch.object(PR, "status", lambda vault: STATUS),
            patch.object(PR, "complete", fake_complete),
            patch.object(CH, "_drain_queue"),
        ):
            PL.run(v, chat["id"], plan)
            _wait(chat["id"])

        messages = _messages(v, chat["id"])
        ready = next(m for m in messages if m.get("kind") == "plan")["plan"]
        result = next(m for m in messages if m.get("kind") == "plan_result")
        self.assertEqual(ready["status"], "stopped")
        self.assertEqual(ready["stop_reason"], "owner")
        self.assertEqual(ready["steps"][0]["status"], "stopped")
        self.assertEqual(ready["steps"][1]["status"], "stopped")
        self.assertIn("Остановлено владельцем", result["text"])
        self.assertEqual(result["plan"]["stop_reason"], "owner")

    def test_a_long_plan_is_not_stopped_by_a_wall_clock(self):
        v = _vault()
        chat = _chat(v)
        plan = _plan(
            v,
            "Сделай отчёт",
            [
                ("harness:deepseek-flash", "DeepSeek Flash", "План", "Составь план"),
                ("claude_code:haiku", "Claude Haiku", "Финал", "Собери отчёт"),
            ],
        )
        clock = {"now": 1000.0}
        calls = []

        def fake_time():
            return clock["now"]

        def fake_complete(vault, pid, model, system, messages, usage=None, meta=None, stop=None):
            calls.append(pid)
            clock["now"] += 95.0  # each step takes longer than any old 90 s cap
            return f"результат шага {len(calls)}"

        with (
            patch.object(PR, "status", lambda vault: STATUS),
            patch.object(PR, "complete", fake_complete),
            patch.object(PL, "time", SimpleNamespace(time=fake_time, monotonic=fake_time, strftime=time.strftime)),
            patch.object(CH, "_drain_queue"),
        ):
            PL.run(v, chat["id"], plan)
            _wait(chat["id"])

        self.assertEqual(len(calls), 2)  # no time limit: both steps ran
        messages = _messages(v, chat["id"])
        ready = next(m for m in messages if m.get("kind") == "plan")["plan"]
        result = next(m for m in messages if m.get("kind") == "plan_result")
        self.assertEqual(ready["status"], "done")
        self.assertNotIn("stop_reason", ready)
        self.assertEqual([s["status"] for s in ready["steps"]], ["ok", "ok"])
        self.assertIn("результат шага 2", result["text"])


if __name__ == "__main__":
    unittest.main()
