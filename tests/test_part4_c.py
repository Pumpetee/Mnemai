"""Часть 4, область C: конструктор схем (экономия всегда включена, «окупается» = 2×, оценка по таблице
средних, правка шагов до запуска), консорциум (фиксированные роли), «открой этот сайт» (интент + open_link)."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())

from mnema.chat import consortium as CO, engine as CH, intents as IN, planner as PL, providers as PR, tools as TL  # noqa: E402
from mnema.memory import init_vault  # noqa: E402
from mnema.vault import Vault  # noqa: E402

STATUS = [
    {
        "id": "harness",
        "name": "DeepSeek Harness",
        "ready": True,
        "models": [
            {"id": "deepseek-flash", "name": "deepseek-flash"},
            {"id": "deepseek-v4-pro", "name": "deepseek-v4-pro"},
        ],
    },
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "ready": True,
        "models": [
            {"id": "anthropic/claude-opus-5", "name": "anthropic/claude-opus-5"},
            {"id": "anthropic/claude-sonnet-4.6", "name": "anthropic/claude-sonnet-4.6"},
        ],
    },
]
LOCAL_STATUS = [
    {"id": "local", "name": "На этом компьютере", "ready": True, "models": [{"id": "qwen3", "name": "Qwen3 8B"}]}
]


def _vault() -> Vault:
    v = Vault(Path(tempfile.mkdtemp()))
    init_vault(v)
    return v


def _chat(v: Vault) -> dict:
    chat = {
        "id": "c4abcdef123456",
        "title": "Тест",
        "model": "harness:deepseek-flash",
        "created": CH._now(),
        "session": CH.current_session(v)["id"],
        "messages": [],
    }
    CH.save_chat(v, chat)
    return chat


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
        folder = v.root / "00 Inbox" / "Схемы"
        folder.mkdir(parents=True, exist_ok=True)
        plan["doc"] = str(folder / "plan.md")
    return plan


def _wait(chat_id: str, tries: int = 200) -> None:
    for _ in range(tries):
        if (CH._gen.get(chat_id) or {}).get("done"):
            return
        import time

        time.sleep(0.02)


class EconomyAlwaysOn(unittest.TestCase):
    def test_economy_off_flag_is_ignored_by_fallback(self):
        v = _vault()
        with patch.object(PR, "status", lambda vault: STATUS):
            off = PL.fallback_plans(v, "Напиши письмо клиенту", economy=False)
            on = PL.fallback_plans(v, "Напиши письмо клиенту", economy=True)
        # economy is on either way: the flag changes nothing, the plans are identical
        self.assertEqual(off, on)

    def test_propose_marks_every_plan_economy_on_even_when_asked_off(self):
        v = _vault()
        with (
            patch.object(PR, "status", lambda vault: STATUS),
            patch.object(PR, "complete", lambda *a, **k: ""),  # the planner model answers nothing → fallback
        ):
            plans = PL.propose(v, "Составь отчёт", budget=0.5, economy=False)
        self.assertEqual(len(plans), 3)
        for p in plans:
            self.assertTrue(p["economy"])
            self.assertTrue(p["steps"])


class Payoff2x(unittest.TestCase):
    def test_a_model_above_twice_the_cheap_step_drops_to_the_cheap_one(self):
        v = _vault()
        plan = _plan(v, "Задача", [])
        plan["steps"] = [
            {
                "role": "Разбор",
                "instruction": "Разбери задачу",
                "out": "план",
                "model": "openrouter:anthropic/claude-opus-5",
                "model_name": "anthropic/claude-opus-5",
                "provider": "OpenRouter",
            },
            {
                "role": "Финал",
                "instruction": "Собери итог",
                "out": "финал",
                "model": "harness:deepseek-v4-pro",
                "model_name": "deepseek-v4-pro",
                "provider": "DeepSeek Harness",
            },
        ]
        with patch.object(PR, "status", lambda vault: STATUS):
            PL._cap_expensive_steps(plan, PL.available(v), "Задача", 0)
        # the baseline is the plan's own cheapest paid step (harness pro, 1/3): opus (15/75) is above 2× and
        # drops to it; the pro step itself stays
        self.assertEqual(plan["steps"][0]["model"], "harness:deepseek-v4-pro")
        self.assertTrue(plan["steps"][0]["downgraded"])
        self.assertEqual(plan["steps"][1]["model"], "harness:deepseek-v4-pro")
        self.assertNotIn("downgraded", plan["steps"][1])

    def test_free_models_only_means_nothing_to_cap(self):
        v = _vault()
        plan = _plan(v, "Задача", [])
        plan["steps"] = [
            {
                "role": "Разбор",
                "instruction": "Разбери задачу",
                "out": "план",
                "model": "local:qwen3",
                "model_name": "Qwen3 8B",
                "provider": "На этом компьютере",
            },
        ]
        with patch.object(PR, "status", lambda vault: LOCAL_STATUS):
            PL._cap_expensive_steps(plan, PL.available(v), "Задача", 0)
        self.assertEqual(plan["steps"][0]["model"], "local:qwen3")
        self.assertNotIn("downgraded", plan["steps"][0])


class AverageTable(unittest.TestCase):
    def test_the_table_holds_only_the_known_numbers(self):
        self.assertEqual(PL.AVG_SPEED, {"local": 40.0, "ollama": 45.0, "strata": 60.0})
        self.assertEqual(PL.CLOUD_SPEED, 220.0)
        self.assertEqual(PL.CHARS_PER_TOKEN, 3.2)

    def test_estimate_uses_the_table(self):
        v = _vault()
        plan = _plan(v, "Задача", [])
        plan["steps"] = [
            {
                "role": "Ответ",
                "instruction": "И",
                "out": "ответ",
                "model": "local:qwen3",
                "model_name": "Qwen3 8B",
                "provider": "На этом компьютере",
            },
        ]
        PL.estimate(plan, "З", context_chars=0)
        est = plan["steps"][0]["est"]
        input_chars = 500 + max(1, int(len("З") * 1.1)) + max(1, int(len("И") * 1.1))
        self.assertEqual(est["in"], round(input_chars / PL.CHARS_PER_TOKEN))
        self.assertEqual(est["out"], round(1500 / PL.CHARS_PER_TOKEN))
        self.assertEqual(est["seconds"], round(2.5 + 1500 / PL.AVG_SPEED["local"] + 1.2, 1))
        self.assertEqual(est["tokens"], round(input_chars / PL.CHARS_PER_TOKEN + 1500 / PL.CHARS_PER_TOKEN))


class StepEditingAccepted(unittest.TestCase):
    def test_run_accepts_an_edited_plan(self):
        v = _vault()
        chat = _chat(v)
        plan = _plan(
            v,
            "Сделай отчёт",
            [
                ("harness:deepseek-flash", "DeepSeek Flash", "План", "Составь план отчёта"),
                ("openrouter:anthropic/claude-opus-5", "anthropic/claude-opus-5", "Финал", "Собери отчёт"),
            ],
        )
        # the owner edits the second step before the launch, as the constructor allows
        plan["steps"][1]["instruction"] = "Собери отчёт по-другому, коротко"
        plan["steps"][1]["model"] = "harness:deepseek-flash"
        plan["steps"][1]["model_name"] = "DeepSeek Flash"
        plan["steps"][1]["provider"] = "DeepSeek Harness"
        calls = []

        def fake_complete(vault, pid, model, system, messages, usage=None, meta=None, stop=None):
            calls.append((pid, messages[0]["text"]))
            return f"результат шага {len(calls)}"

        with (
            patch.object(PR, "status", lambda vault: STATUS),
            patch.object(PR, "complete", fake_complete),
            patch.object(CH, "_drain_queue"),
        ):
            PL.run(v, chat["id"], plan)
            _wait(chat["id"])

        ready = next(m for m in CH.load_chat(v, chat["id"])["messages"] if m.get("kind") == "plan")["plan"]
        self.assertEqual(ready["status"], "done")
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0], "harness")  # the edited executor runs the second step
        self.assertEqual(calls[1][0], "harness")
        self.assertIn("по-другому, коротко", calls[1][1])  # the edited instruction goes to the model
        self.assertEqual(ready["steps"][1]["output"], "результат шага 2")


class ConsortiumFixedRoles(unittest.TestCase):
    def test_roles_are_fixed(self):
        cfg = {"members": ["a:x", "b:y"], "summarizer": "b:y", "roles": {"a:x": "skeptic"}}
        self.assertIn("ведущий", CO.fixed_role(cfg, "a:x"))
        self.assertIn("участник", CO.fixed_role(cfg, "b:y"))
        self.assertIn("суммаризатор", CO.fixed_role(cfg, "b:y", final=True))
        self.assertIn("ведущий", CO.fixed_role(cfg, "a:x", final=True))  # the leader stays the leader
        # a role the owner picked earlier no longer changes the discussion
        self.assertNotIn("Скептик", CO.fixed_role(cfg, "a:x"))
        self.assertNotIn("Скептик", CO.fixed_role(cfg, "a:x", final=True))


class OpenThisSite(unittest.TestCase):
    def setUp(self):
        self.v = _vault()

    def test_open_link_is_a_registered_tool_with_a_permission_card_text(self):
        self.assertIn("open_link", TL.TOOLS)
        self.assertIn("open_link", TL.WRITES)  # like the other computer commands: the card asks the owner
        call = TL.parse('```mnema open_link url="https://example.com"\n```')
        self.assertEqual(call["tool"], "open_link")
        self.assertEqual(call["url"], "https://example.com")
        self.assertIn("https://example.com", TL.what(self.v, {"tool": "open_link", "url": "https://example.com"}))

    def test_the_phrase_is_recognised_only_for_this_command(self):
        self.assertTrue(IN.is_this_site("открой этот сайт"))
        self.assertTrue(IN.is_this_site("Открой эту ссылку, пожалуйста"))
        self.assertTrue(IN.is_this_site("откройте этот сайт"))
        self.assertFalse(IN.is_this_site("открой гугл"))
        self.assertFalse(IN.is_this_site("что за сайт"))

    def test_link_from_chat_finds_the_message_and_the_attachment(self):
        chat = {
            "id": "x1",
            "messages": [
                {"role": "user", "text": "глянь https://habr.com/ru/articles/1 — там статья"},
                {"role": "user", "text": "открой этот сайт"},
            ],
        }
        self.assertEqual(IN.link_from(chat), "https://habr.com/ru/articles/1")
        tp = Path(tempfile.mkdtemp()) / "file.txt"
        tp.write_text("внутри файла ссылка https://example.org/a", encoding="utf-8")
        chat["messages"] = [
            {"role": "user", "text": "файл с ссылкой", "files": [{"name": "file.txt", "text_path": str(tp)}]},
            {"role": "user", "text": "открой этот сайт"},
        ]
        self.assertEqual(IN.link_from(chat), "https://example.org/a")
        chat["messages"] = [{"role": "user", "text": "без ссылок"}, {"role": "user", "text": "открой этот сайт"}]
        self.assertIsNone(IN.link_from(chat))

    def test_send_opens_the_link_without_calling_the_model(self):
        v = self.v
        chat = _chat(v)
        CH.modify_chat(
            v,
            chat["id"],
            lambda c: c["messages"].append(
                {"role": "user", "text": "вот статья: https://example.com/page", "ts": CH._now()}
            ),
        )
        opened = []

        with (
            patch.object(PR, "stream", side_effect=AssertionError("the model must not be called")),
            patch.object(
                TL, "_open_app", lambda vault, call, client="owner": opened.append(call["name"]) or ("ок", "ок", "")
            ),
        ):
            r = CH.send(v, "открой этот сайт", cid=chat["id"], model="harness:deepseek-flash", sync=True, learn=False)
        self.assertEqual(r["chat"], chat["id"])
        msgs = CH.load_chat(v, chat["id"])["messages"]
        self.assertEqual(msgs[-1]["role"], "assistant")
        self.assertIn("открыла ссылку", msgs[-1]["text"])
        self.assertEqual(opened, ["https://example.com/page"])
