"""Правило «окупается = не дороже 2× цены дешёвого шага»: baseline считается внутри плана, а специализированные
scaledown-модели (extract/summarize) не подбираются исполнителями — баг «scale down вместо моделей»."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())

from mnema.chat import planner as PL, providers as PR  # noqa: E402
from mnema.memory import init_vault  # noqa: E402
from mnema.vault import Vault  # noqa: E402

FLASH = "harness:deepseek-flash"
PRO = "harness:deepseek-v4-pro"
OPUS = "openrouter:anthropic/claude-opus-5"
EXTRACT = "openrouter:scaledown/extract"
SUMMARIZE = "openrouter:scaledown/summarize"
LOCAL = "local:qwen3"

# the prices of the owner's catalog: the scaledown helpers are almost free
PRICES = {
    ("harness", "deepseek-flash"): (0.28, 0.42),
    ("harness", "deepseek-v4-pro"): (1.0, 3.0),
    ("openrouter", "anthropic/claude-opus-5"): (15.0, 75.0),
    ("openrouter", "scaledown/extract"): (0.001, 0.001),
    ("openrouter", "scaledown/summarize"): (0.001, 0.001),
    ("local", "qwen3"): (0.0, 0.0),
}

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
            {"id": "scaledown/extract", "name": "scaledown/extract"},
            {"id": "scaledown/summarize", "name": "scaledown/summarize"},
            {"id": "anthropic/claude-opus-5", "name": "anthropic/claude-opus-5"},
        ],
    },
    {"id": "local", "name": "На этом компьютере", "ready": True, "models": [{"id": "qwen3", "name": "Qwen3 8B"}]},
]


def _vault() -> Vault:
    v = Vault(Path(tempfile.mkdtemp()))
    init_vault(v)
    return v


def _step(model: str, model_name: str, role: str, provider: str) -> dict:
    return {
        "role": role,
        "instruction": f"инструкция {role}",
        "out": "ответ",
        "model": model,
        "model_name": model_name,
        "provider": provider,
    }


def _price(pid: str, name: str) -> tuple:
    return PRICES.get((pid, name.lower()), (1.0, 3.0))


def _cap(plan: dict) -> dict:
    with patch.object(PL, "_price", side_effect=_price):
        return PL._cap_expensive_steps(plan, [], "Задача", 0)


class BaselineInsidePlan(unittest.TestCase):
    def test_opus_drops_to_the_plans_own_flash_not_to_the_catalog_cheapest(self):
        plan = {
            "steps": [
                _step(FLASH, "deepseek-flash", "Разбор", "DeepSeek Harness"),
                _step(OPUS, "anthropic/claude-opus-5", "Черновик", "OpenRouter"),
                _step(FLASH, "deepseek-flash", "Правки", "DeepSeek Harness"),
            ]
        }
        _cap(plan)
        # the catalog's cheapest paid model is scaledown/extract, but the baseline is the plan's own Flash:
        # Opus drops to Flash, never to a scaledown helper
        self.assertEqual(plan["steps"][1]["model"], FLASH)
        self.assertTrue(plan["steps"][1]["downgraded"])
        self.assertEqual([s["model"] for s in plan["steps"]], [FLASH, FLASH, FLASH])
        self.assertNotIn("downgraded", plan["steps"][0])
        self.assertNotIn("downgraded", plan["steps"][2])

    def test_all_cheap_steps_stay_untouched(self):
        plan = {
            "steps": [
                _step(FLASH, "deepseek-flash", "Разбор", "DeepSeek Harness"),
                _step(FLASH, "deepseek-flash", "Финал", "DeepSeek Harness"),
            ]
        }
        _cap(plan)
        self.assertEqual([s["model"] for s in plan["steps"]], [FLASH, FLASH])
        for s in plan["steps"]:
            self.assertNotIn("downgraded", s)

    def test_free_steps_are_never_touched(self):
        plan = {
            "steps": [
                _step(LOCAL, "qwen3", "Разбор", "На этом компьютере"),
                _step(OPUS, "anthropic/claude-opus-5", "Финал", "OpenRouter"),
                _step(LOCAL, "qwen3", "Правки", "На этом компьютере"),
            ]
        }
        _cap(plan)
        self.assertEqual(plan["steps"][0]["model"], LOCAL)
        self.assertEqual(plan["steps"][2]["model"], LOCAL)
        self.assertNotIn("downgraded", plan["steps"][0])
        self.assertNotIn("downgraded", plan["steps"][2])

    def test_scaledown_never_becomes_a_fresh_target(self):
        plan = {
            "steps": [
                _step(EXTRACT, "scaledown/extract", "Извлечение", "OpenRouter"),
                _step(FLASH, "deepseek-flash", "Разбор", "DeepSeek Harness"),
                _step(OPUS, "anthropic/claude-opus-5", "Черновик", "OpenRouter"),
            ]
        }
        _cap(plan)
        # the extract step itself stays (it is part of the plan), Opus drops to the plan's ordinary cheap step
        self.assertEqual(plan["steps"][0]["model"], EXTRACT)
        self.assertEqual(plan["steps"][1]["model"], FLASH)
        self.assertEqual(plan["steps"][2]["model"], FLASH)
        for s in plan["steps"][1:]:
            self.assertNotIn("extract", s["model"].lower())
            self.assertNotIn("summarize", s["model"].lower())
        self.assertTrue(plan["steps"][2]["downgraded"])


class RolesDistributeExecutors(unittest.TestCase):
    def test_quality_fallback_gives_the_critic_a_strong_model(self):
        v = _vault()
        with patch.object(PR, "status", lambda vault: STATUS), patch.object(PL, "_price", side_effect=_price):
            plans = PL.fallback_plans(v, "Сделай отчёт")
        quality = next(p for p in plans if p["id"] == "quality")
        critic = next(s for s in quality["steps"] if s["role"] == "Критик")
        self.assertIn("openrouter", critic["model"])  # критика — сильная модель, а не DeepSeek Flash
        for s in quality["steps"]:
            if s["role"] != "Критик":
                self.assertNotIn("openrouter", s["model"])

    def test_fast_stays_cheap(self):
        v = _vault()
        with patch.object(PR, "status", lambda vault: STATUS), patch.object(PL, "_price", side_effect=_price):
            plans = PL.fallback_plans(v, "Сделай отчёт")
        fast = next(p for p in plans if p["id"] == "fast")
        self.assertTrue(fast["steps"])
        for s in fast["steps"]:
            self.assertIn(s["model"].split(":", 1)[0], PL.FREE)


class CriticalStepsAboveCap(unittest.TestCase):
    def _plan(self) -> dict:
        return {
            "steps": [
                _step(FLASH, "deepseek-flash", "Разбор", "DeepSeek Harness"),
                _step(OPUS, "anthropic/claude-opus-5", "Критик", "OpenRouter"),
                _step(OPUS, "anthropic/claude-opus-5", "Финал", "OpenRouter"),
                _step(OPUS, "anthropic/claude-opus-5", "Черновик", "OpenRouter"),
            ]
        }

    def test_not_more_than_two_steps_above_the_cap(self):
        plan = self._plan()
        _cap(plan)
        opus = [s for s in plan["steps"] if s["model"] == OPUS]
        self.assertEqual(len(opus), 2)  # критик и финал остались дорогими, не больше двух

    def test_the_third_expensive_step_is_downgraded(self):
        plan = self._plan()
        _cap(plan)
        draft = next(s for s in plan["steps"] if s["role"] == "Черновик")
        self.assertEqual(draft["model"], FLASH)
        self.assertTrue(draft["downgraded"])

    def test_a_critical_step_above_the_cap_stays(self):
        plan = {
            "steps": [
                _step(FLASH, "deepseek-flash", "Разбор", "DeepSeek Harness"),
                _step(OPUS, "anthropic/claude-opus-5", "Критик", "OpenRouter"),
            ]
        }
        _cap(plan)
        self.assertEqual(plan["steps"][1]["model"], OPUS)
        self.assertNotIn("downgraded", plan["steps"][1])


class FallbackAvoidsScaledown(unittest.TestCase):
    def test_fallback_steps_do_not_take_extract_or_summarize(self):
        v = _vault()
        with patch.object(PR, "status", lambda vault: STATUS), patch.object(PL, "_price", side_effect=_price):
            plans = PL.fallback_plans(v, "Напиши письмо клиенту")
        models = [s["model"] for p in plans for s in p["steps"]]
        self.assertTrue(models)
        for m in models:
            self.assertNotIn("extract", m.lower())
            self.assertNotIn("summarize", m.lower())
        # with a free local model and an ordinary harness model connected, the ordinary one is used, not scaledown
        self.assertTrue(any(m.startswith("local:") for m in models))
        self.assertTrue(any(m == FLASH for m in models))


LITE = "harness:amazon/nova-lite-v1"
STATUS_LITE = [
    {
        "id": "harness",
        "name": "DeepSeek Harness",
        "ready": True,
        "models": [
            {"id": "amazon/nova-lite-v1", "name": "amazon/nova-lite-v1"},
            {"id": "deepseek-flash", "name": "deepseek-flash"},
        ],
    },
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "ready": True,
        "models": [{"id": "anthropic/claude-opus-5", "name": "anthropic/claude-opus-5"}],
    },
]


class WeakModelsNotChosen(unittest.TestCase):
    def test_thorough_plans_skip_lite_models_but_fast_may_take_them(self):
        v = _vault()
        with patch.object(PR, "status", lambda vault: STATUS_LITE):
            plans = PL.fallback_plans(v, "Сделай отчёт")
        fast = next(p for p in plans if p["id"] == "fast")
        optimal = next(p for p in plans if p["id"] == "optimal")
        quality = next(p for p in plans if p["id"] == "quality")
        # «Быстро» — самое дешёвое: lite-модель допустима
        self.assertTrue(any("nova-lite" in s["model"] for s in fast["steps"]))
        # «Оптимально»/«Качественно» — lite-модель не выбирается, пока есть обычная
        for s in optimal["steps"] + quality["steps"]:
            self.assertNotIn("nova-lite", s["model"])
            self.assertNotIn("lite", s["model"].lower())

    def test_auto_planner_never_offers_a_lite_model(self):
        v = _vault()
        with patch.object(PR, "status", lambda vault: STATUS_LITE):
            rows = PL.available(v)
            planner = PL._planner(rows, "auto")
        self.assertEqual(planner["model"], "harness:deepseek-flash")  # lite стоит первым по имени, но auto её не берёт


RETRY_STATUS = [
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
        "models": [{"id": "anthropic/claude-opus-5", "name": "anthropic/claude-opus-5"}],
    },
]
TOOL_BLOCK = '```mnema read_file path="нет.md"\n```'


def _chat(v: Vault) -> dict:
    from mnema.chat import engine as CH

    chat = {
        "id": "c4e500000001",
        "title": "План",
        "model": "harness:deepseek-flash",
        "created": CH._now(),
        "session": CH.current_session(v)["id"],
        "messages": [],
    }
    CH.save_chat(v, chat)
    return chat


def _wait(chat_id: str, tries: int = 400) -> None:
    import time

    from mnema.chat import engine as CH

    for _ in range(tries):
        if (CH._gen.get(chat_id) or {}).get("done"):
            return
        time.sleep(0.02)


class StepRetry(unittest.TestCase):
    def _run_plan(self, plan, fake_complete):
        from mnema.chat import engine as CH, tools as TL

        v = _vault()
        chat = _chat(v)

        def fake_parse(text):
            return {"tool": "read_file", "path": "нет.md", "start": 0, "end": len(text)} if "mnema" in text else None

        with (
            patch.object(PR, "status", lambda vault: RETRY_STATUS),
            patch.object(PR, "complete", fake_complete),
            patch.object(TL, "enabled", lambda vault: True),
            patch.object(TL, "rule", lambda vault, small=False: "ПРАВИЛО ИНСТРУМЕНТОВ"),
            patch.object(TL, "parse", fake_parse),
            patch.object(TL, "before", lambda text, call: ""),
            patch.object(CH, "_act", lambda *args, **kwargs: "такого файла нет"),
            patch.object(CH, "_drain_queue"),
        ):
            PL.run(v, chat["id"], plan)
            _wait(chat["id"])
        messages = CH.load_chat(v, chat["id"])["messages"]
        ready = next(m for m in messages if m.get("kind") == "plan")["plan"]
        result = next(m for m in messages if m.get("kind") == "plan_result")
        return ready, result

    def test_a_looped_step_is_retried_on_another_model_and_the_plan_continues(self):
        flash_calls = {"n": 0}

        def fake_complete(vault, pid, model, system, messages, usage=None, meta=None, stop=None):
            if pid == "harness" and model == "deepseek-v4-pro":
                return TOOL_BLOCK  # nova-style weak executor: asks the same thing over and over
            if pid == "harness":
                flash_calls["n"] += 1
                return "результат шага 1" if flash_calls["n"] == 1 else "результат шага 3"
            return "результат шага 2"  # the retry on the strong openrouter model

        plan = {
            "id": "optimal",
            "title": "Оптимально",
            "task": "Отчёт",
            "steps": [
                _step("harness:deepseek-flash", "deepseek-flash", "Разбор", "DeepSeek Harness"),
                _step("harness:deepseek-v4-pro", "deepseek-v4-pro", "Черновик", "DeepSeek Harness"),
                _step("harness:deepseek-flash", "deepseek-flash", "Финал", "DeepSeek Harness"),
            ],
        }
        ready, result = self._run_plan(plan, fake_complete)
        self.assertEqual(ready["status"], "done")
        step2 = ready["steps"][1]
        self.assertEqual(step2["status"], "ok")
        self.assertEqual(step2["model"], "openrouter:anthropic/claude-opus-5")
        self.assertEqual(step2["retried"]["reason"], "loop")
        self.assertIn("deepseek-v4-pro", step2["retried"]["from"])
        self.assertIn("повторён", step2["note"])  # the card shows what happened
        self.assertEqual(ready["steps"][2]["status"], "ok")
        self.assertEqual(ready["steps"][2]["output"], "результат шага 3")
        self.assertEqual(result["text"], "результат шага 3")

    def test_retry_is_limited_to_two_per_plan(self):
        opus_calls = {"n": 0}

        def fake_complete(vault, pid, model, system, messages, usage=None, meta=None, stop=None):
            if pid == "harness" and model == "deepseek-v4-pro":
                return TOOL_BLOCK
            if pid == "openrouter":
                opus_calls["n"] += 1
                return f"результат после повтора {opus_calls['n']}"
            return "результат шага 1"

        plan = {
            "id": "quality",
            "title": "Качественно",
            "task": "Отчёт",
            "steps": [
                _step("harness:deepseek-flash", "deepseek-flash", "Разбор", "DeepSeek Harness"),
                _step("harness:deepseek-v4-pro", "deepseek-v4-pro", "Черновик", "DeepSeek Harness"),
                _step("harness:deepseek-v4-pro", "deepseek-v4-pro", "Правки", "DeepSeek Harness"),
                _step("harness:deepseek-v4-pro", "deepseek-v4-pro", "Финал", "DeepSeek Harness"),
            ],
        }
        ready, result = self._run_plan(plan, fake_complete)
        self.assertEqual(ready["status"], "stopped")  # третий упавший шаг уже без повтора
        self.assertEqual(ready["stop_reason"], "loop")
        self.assertIsNotNone(ready["steps"][1].get("retried"))
        self.assertIsNotNone(ready["steps"][2].get("retried"))
        self.assertNotIn("retried", ready["steps"][3])  # лимит повторов на план исчерпан
        self.assertEqual(ready["steps"][3]["status"], "stopped")
        self.assertIn("шаге 4 из 4", result["text"])

    def test_if_the_retry_fails_too_the_plan_stops_with_a_reason(self):
        def fake_complete(vault, pid, model, system, messages, usage=None, meta=None, stop=None):
            if pid == "harness" and model == "deepseek-flash":
                return "результат шага 1"
            return TOOL_BLOCK  # и первый исполнитель, и модель повтора зацикливаются

        plan = {
            "id": "optimal",
            "title": "Оптимально",
            "task": "Отчёт",
            "steps": [
                _step("harness:deepseek-flash", "deepseek-flash", "Разбор", "DeepSeek Harness"),
                _step("harness:deepseek-v4-pro", "deepseek-v4-pro", "Черновик", "DeepSeek Harness"),
            ],
        }
        ready, result = self._run_plan(plan, fake_complete)
        self.assertEqual(ready["status"], "stopped")
        self.assertEqual(ready["stop_reason"], "loop")
        step2 = ready["steps"][1]
        self.assertEqual(step2["status"], "stopped")
        self.assertIsNotNone(step2.get("retried"))
        self.assertEqual(step2["retried"]["reason"], "loop")
        self.assertIn("План остановлен", result["text"])
        self.assertIn("Черновик", result["text"])
