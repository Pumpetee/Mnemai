"""The constructor's money side: economy is on by default, a budget (recommended or the owner's) caps the
scheme, and a scheme that does not fit is downgraded to the cheapest connected models instead of burning money."""

import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())

from mnema.chat import planner as PL, providers as PR  # noqa: E402
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


def _vault() -> Vault:
    v = Vault(Path(tempfile.mkdtemp()))
    init_vault(v)
    return v


class Prices(unittest.TestCase):
    def test_opus_and_haiku_through_openrouter_are_not_mistaken_for_a_cheap_model(self):
        self.assertEqual(PL._price("openrouter", "anthropic/claude-opus-5"), (15.0, 75.0))
        self.assertEqual(PL._price("openrouter", "anthropic/claude-haiku-4"), (1.0, 5.0))
        self.assertEqual(PL._price("openrouter", "anthropic/claude-sonnet-4.6"), (3.0, 15.0))
        self.assertEqual(PL._price("harness", "deepseek-flash")[0], 0.28)


class EconomyAndBudget(unittest.TestCase):
    def test_economy_plan_takes_no_strong_models(self):
        v = _vault()
        with patch.object(PR, "status", lambda vault: STATUS):
            plans = PL.fallback_plans(v, "Напиши письмо клиенту", economy=True)
        models = {s["model"] for p in plans for s in p["steps"]}
        self.assertTrue(models)
        self.assertFalse([m for m in models if "openrouter" in m], models)

    def test_quality_still_has_more_steps_than_fast(self):
        v = _vault()
        with patch.object(PR, "status", lambda vault: STATUS):
            plans = PL.fallback_plans(v, "Сделай отчёт", economy=True)
        self.assertGreater(len(plans[2]["steps"]), len(plans[0]["steps"]))
        self.assertEqual(len(plans[2]["steps"]), 5)

    def test_recommended_budget_covers_the_cheap_quality_plan(self):
        v = _vault()
        task = "Составь короткий план поездки в Казань на три дня"
        with patch.object(PR, "status", lambda vault: STATUS):
            rec = PL.recommend_budget(v, task)
            cheap = next(p for p in PL.fallback_plans(v, task, economy=True) if p["id"] == "quality")
        self.assertGreater(rec["usd"], 0)
        self.assertGreaterEqual(rec["usd"], cheap["estimate"]["cost_max"] - 1e-9)

    def test_fit_budget_downgrades_strong_steps_and_counts_the_difference(self):
        v = _vault()
        task = "Напиши письмо"
        plan = {
            "id": "quality",
            "title": "Качественно",
            "note": "",
            "task": task,
            "steps": [
                {
                    "role": "Черновик",
                    "instruction": "Напиши",
                    "out": "черновик",
                    "model": "openrouter:anthropic/claude-opus-5",
                    "model_name": "anthropic/claude-opus-5",
                    "provider": "OpenRouter",
                },
                {
                    "role": "Финал",
                    "instruction": "Сократи",
                    "out": "финал",
                    "model": "openrouter:anthropic/claude-opus-5",
                    "model_name": "anthropic/claude-opus-5",
                    "provider": "OpenRouter",
                },
            ],
        }
        with patch.object(PR, "status", lambda vault: STATUS):
            rows = PL.available(v)
            PL.estimate(plan, task)
            before = plan["estimate"]["cost_min"]
            PL._fit_budget(plan, rows, budget=0.01, task=task, context_chars=0)
        self.assertLess(plan["estimate"]["cost_min"], before)
        self.assertTrue(all("openrouter" not in s["model"] for s in plan["steps"]))
        self.assertTrue(plan["budget"]["fit"])

    def test_fit_budget_is_honest_when_even_the_cheapest_chain_is_over(self):
        v = _vault()
        task = "Очень длинная задача"
        plan = {
            "id": "fast",
            "title": "Быстро",
            "note": "",
            "task": task,
            "steps": [
                {
                    "role": "Ответ",
                    "instruction": "Ответь",
                    "out": "ответ",
                    "model": "harness:deepseek-flash",
                    "model_name": "deepseek-flash",
                    "provider": "DeepSeek Harness",
                }
            ],
        }
        with patch.object(PR, "status", lambda vault: STATUS):
            rows = PL.available(v)
            PL._fit_budget(plan, rows, budget=0.00001, task=task, context_chars=200_000)
        self.assertFalse(plan["budget"]["fit"])
        self.assertGreater(plan["budget"]["min_usd"], 0.00001)

    def test_propose_fits_every_variant_into_the_owner_budget(self):
        v = _vault()
        with (
            patch.object(PR, "status", lambda vault: STATUS),
            patch.object(PR, "complete", side_effect=RuntimeError("нет сети")),
        ):
            plans = PL.propose(v, "Составь чек-лист по безопасности Linux", budget=0.05, economy=True)
        self.assertEqual(len(plans), 3)
        for plan in plans:
            self.assertTrue(plan["budget"]["fit"], (plan["id"], plan["budget"], plan["estimate"]))
            self.assertLessEqual(plan["estimate"]["cost_min"], 0.05 + 1e-9)
            self.assertTrue(plan["economy"])
            self.assertGreater(plan["budget"]["recommended"], 0)

    def test_propose_is_economy_by_default(self):
        v = _vault()
        with (
            patch.object(PR, "status", lambda vault: STATUS),
            patch.object(PR, "complete", side_effect=RuntimeError("нет сети")),
        ):
            plans = PL.propose(v, "Объясни, что такое MCP")
        self.assertTrue(all(p["economy"] for p in plans))
        self.assertGreater(plans[0]["budget"]["recommended"], 0)

    def test_propose_marks_a_budget_that_is_too_small(self):
        v = _vault()
        with (
            patch.object(PR, "status", lambda vault: STATUS),
            patch.object(PR, "complete", side_effect=RuntimeError("нет сети")),
        ):
            plans = PL.propose(v, "Составь длинный отчёт", budget=0.0005, economy=True)
        self.assertFalse(plans[2]["budget"]["fit"])
        self.assertGreater(plans[2]["budget"]["min_usd"], 0.0005)


if __name__ == "__main__":
    unittest.main()


class ExactOpenRouterPrices(unittest.TestCase):
    def test_usd_per_1m_parses_openrouter_strings(self):
        self.assertEqual(PR._usd_per_1m("0.000015"), 15.0)
        self.assertEqual(PR._usd_per_1m("$0.000003"), 3.0)
        self.assertEqual(PR._usd_per_1m("0"), 0.0)
        self.assertEqual(PR._usd_per_1m(None), 0.0)

    def test_fetch_saves_exact_prices_even_before_the_balance_check(self):
        v = _vault()
        data = [
            {
                "id": "models/anthropic/claude-opus-5",
                "created": 1700000000,
                "pricing": {"prompt": "0.000015", "completion": "0.000075"},
            },
            {
                "id": "models/qwen/qwen3-coder",
                "created": 1700000001,
                "pricing": {"prompt": "0.0000002", "completion": "0.0000008"},
            },
        ]

        def fake_get(url, headers):
            if url.endswith("/key"):
                raise urllib.error.HTTPError(url, 402, "Payment Required", {}, None)  # no balance, prices still saved
            return {"data": data}

        with patch.object(PR, "_get", side_effect=fake_get), patch.object(PR, "key_of", return_value="sk-test"):
            with self.assertRaises(urllib.error.HTTPError):
                PR.fetch_models(v, "openrouter")
        prices = PR.load(v)["openrouter"]["prices"]
        self.assertEqual(prices["anthropic/claude-opus-5"], [15.0, 75.0])
        self.assertEqual(prices["qwen/qwen3-coder"], [0.2, 0.8])

    def test_planner_uses_the_exact_price_when_known(self):
        v = _vault()
        PR.save(v, "openrouter", prices={"qwen/qwen3-coder": [1.23, 4.56]})
        with patch.object(PR, "status", lambda vault: STATUS):
            PL.available(v)  # loads the cache
        self.assertEqual(PL._price("openrouter", "qwen/qwen3-coder"), (1.23, 4.56))
        self.assertEqual(PL._price("openrouter", "anthropic/claude-opus-5"), (15.0, 75.0))  # the guide still works
