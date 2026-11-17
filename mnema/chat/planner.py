"""Visual task plans: several ways to split one job between the connected AIs.

A plan is a small schema — an ordered chain of steps. Every step has its own AI (from the models that are
connected right now), a role and an instruction; each step gets the task and the previous results. Three
variants are offered (fast, balanced, quality) with estimates of time and tokens, and the owner chooses one.
Running a plan is sequential: no external service, no subscription — only the keys and local models that
are already on this computer.
"""

from __future__ import annotations

import json
import re
import secrets
import threading
import time
from pathlib import Path

from ..vault import Vault
from . import engine as CH, providers as PR

MAX_STEPS = 6
# No wall-clock cap on the whole plan, but one provider request must not hang the plan thread forever.
PROVIDER_SECONDS = 300
FREE = {"local", "ollama", "strata"}  # runs on this computer: no token price
STRONG = {"claude_code", "anthropic", "openai", "gemini", "openrouter", "codex"}
OUT_CHARS = {"короткий": 700, "план": 1200, "черновик": 3500, "критика": 1000, "финал": 2200, "ответ": 1500}
SPEED = {"local": 40.0, "ollama": 45.0, "strata": 60.0}  # chars per second on this computer
CLOUD_SPEED = 220.0  # chars per second of cloud streaming, a rough but honest order of magnitude
RECOMMEND_FACTOR = 1.5  # a margin over the cheap «Качественно» estimate: a recommendation must not cut the budget
RECOMMEND_MIN = 0.01

# USD per 1M tokens: an approximate list price, only to compare the variants with each other.
# Local models are free; Claude Code is covered by the subscription, the price below is the API equivalent.
PRICE_IN_OUT = {
    "local": (0.0, 0.0),
    "ollama": (0.0, 0.0),
    "strata": (0.0, 0.0),
    "harness": (0.28, 0.42),
    "deepseek": (0.28, 0.42),
    "claude_code": (3.0, 15.0),
    "anthropic": (3.0, 15.0),
    "openai": (2.5, 10.0),
    "gemini": (0.3, 1.2),
    "openrouter": (0.6, 1.8),
    "yandex": (0.5, 1.5),
    "codex": (2.5, 10.0),
    "cursor": (2.5, 10.0),
    "opencode_go": (0.5, 1.5),
}


def _price(pid: str, name: str) -> tuple[float, float]:
    """The cheapest honest thing we can do without a price list per account: a model-name based guide."""
    name = (name or "").lower()
    if pid == "claude_code":
        if "haiku" in name:
            return (1.0, 5.0)
        if "opus" in name:
            return (15.0, 75.0)
        return (3.0, 15.0)
    if pid in ("harness", "deepseek"):
        return (1.0, 3.0) if "pro" in name else (0.28, 0.42)  # Flash is cheap, V4 Pro is the dear one
    if pid == "openrouter":
        if "mini" in name or "flash" in name:
            return (0.2, 0.8)
        if "opus" in name:
            return (15.0, 75.0)
        if "haiku" in name:
            return (1.0, 5.0)
        if "sonnet" in name:
            return (3.0, 15.0)
        if "gemini" in name:
            return (0.3, 1.2)
        if "gpt" in name:
            return (2.5, 10.0)
        if "aion-3.5" in name:
            return (1.0, 3.0)
        return (0.6, 1.8)
    return PRICE_IN_OUT.get(pid, (1.0, 3.0))


def _money(lo: float, hi: float | None = None) -> str:
    hi = lo if hi is None else hi

    def one(v: float) -> str:
        if v <= 0:
            return "$0"
        return f"${v:.4f}" if v < 0.01 else f"${v:.2f}"

    return one(lo) if abs(hi - lo) < 1e-9 else f"{one(lo)}–{one(hi)}"


def _tokens_text(n: int) -> str:
    return f"{int(n):,}".replace(",", " ")


def _steps_word(n: int) -> str:
    if 11 <= n % 100 <= 14:
        return "шагов"
    if n % 10 == 1:
        return "шаг"
    if 2 <= n % 10 <= 4:
        return "шага"
    return "шагов"


def available(vault: Vault) -> list[dict]:
    """Every model that can answer right now, cheapest/local first."""
    rows: list[dict] = []
    for p in PR.status(vault):
        if not p.get("ready"):
            continue
        for m in p.get("models") or []:
            pid = p["id"]
            rows.append(
                {
                    "model": f"{pid}:{m['id']}",
                    "name": m.get("name") or m["id"],
                    "provider": p.get("name") or pid,
                    "pid": pid,
                    "free": pid in FREE,
                    "tier": 1 if pid in FREE else 3 if pid in STRONG else 2,
                }
            )
    rows.sort(key=lambda r: (r["tier"], not r["free"], r["name"].lower()))
    return rows


def models_table(vault: Vault) -> list[dict]:
    """Every ready model with the guide prices, for the comparison table in the constructor."""
    out = []
    for row in available(vault):
        pin, pout = _price(row["pid"], row["name"])
        out.append(
            {
                "model": row["model"],
                "name": row["name"],
                "provider": row["provider"],
                "pid": row["pid"],
                "free": row["free"],
                "tier": row["tier"],
                "price_in": pin,
                "price_out": pout,
            }
        )
    return out


def _planner(rows: list[dict], wanted: str) -> dict:
    """Who chooses the executors: the cheapest ready model (auto), a strong one, a local one or an exact model."""
    wanted = (wanted or "").strip()
    if wanted and wanted not in ("auto", "strong", "medium", "local"):
        row = next((r for r in rows if r["model"] == wanted), None)
        if not row:
            raise ValueError("эта модель не подключена")
        return row
    if wanted == "local":
        row = next((r for r in rows if r["free"]), None)
        if not row:
            raise ValueError("нет локальной модели — выбери другого планировщика")
        return row
    if wanted == "strong":
        return max(rows, key=lambda r: (r["tier"], not r["free"]))
    if wanted == "medium":
        middle = next((r for r in rows if r["tier"] == 2 and not r["free"]), None)
        if middle is None:
            middle = next((r for r in rows if r["tier"] == 2), None)
        if middle is None:
            middle = rows[len(rows) // 2]
        return middle
    order = (
        "harness",
        "local",
        "ollama",
        "strata",
        "deepseek",
        "gemini",
        "openai",
        "anthropic",
        "claude_code",
        "openrouter",
    )
    return next((r for pid in order for r in rows if r["pid"] == pid), rows[0])


def _memory(vault: Vault, pid: str) -> str:
    """What Mnemai knows about the owner, as this AI is allowed to see it."""
    try:
        from ..memory import context_for

        text, _ = context_for(vault, pid, log=False)
        return text or ""
    except Exception:  # noqa: BLE001 — a plan must work even if the memory is locked
        return ""


def _history(vault: Vault, cid: str, limit: int = 8, per: int = 1400) -> list[str]:
    """The last messages of this conversation, so a plan does not ask what the owner already said."""
    if not cid:
        return []
    try:
        chat = CH.load_chat(vault, cid)
    except KeyError:
        return []
    out = []
    for m in chat.get("messages") or []:
        text = str(m.get("text") or "").strip()
        if not text or m.get("kind") in ("progress", "action", "plan"):
            continue
        who = "Владелец" if m.get("role") == "user" else "Mnemai"
        out.append(f"{who}: {text[:per]}")
    return out[-limit:]


def _pick(rows: list[dict], want: int, used: set[str]) -> dict | None:
    if not rows:
        return None

    def first_free(pool: list[dict]) -> dict | None:
        return next((row for row in pool if row["model"] not in used), None)

    hit = first_free([r for r in rows if r["tier"] == want])
    if hit:
        return hit
    # economy may run out of cheap executors before it runs out of steps: reuse the cheapest suitable model
    # instead of drifting to an expensive one just because it happens to be free
    allowed = [r for r in _by_cost(rows) if r["tier"] <= max(want, 2)]
    return first_free(allowed) or (allowed or _by_cost(rows))[0]


def _est_chars(text: str) -> int:
    return max(1, int(len(text or "") * 1.1))


def estimate(plan: dict, task: str, context_chars: int = 0) -> dict:
    """Where the numbers come from: memory+history+task+previous answers+instruction, output by role, speed by provider."""
    previous = 0
    total_tokens = total_tokens_hi = 0.0
    total_seconds = total_seconds_hi = total_seconds_lo = 0.0
    total_cost = total_cost_hi = 0.0
    for step in plan.get("steps") or []:
        instruction = str(step.get("instruction") or "")
        input_chars = 500 + context_chars + _est_chars(task) + previous + _est_chars(instruction)
        out_chars = OUT_CHARS.get(str(step.get("out") or "ответ"), 1500)
        pid = str(step.get("model") or "").split(":", 1)[0]
        speed = SPEED.get(pid, CLOUD_SPEED)
        seconds = 2.5 + out_chars / speed + 1.2
        tokens = round(input_chars / 3.2 + out_chars / 3.2)
        tokens_hi = round(tokens * 2.0)  # a real chain came out 1.6× the point estimate
        seconds_hi = round(seconds * 2.2, 1)  # and the real time was about 2×
        seconds_lo = round(seconds * 0.5, 1)  # a short Harness answer took 5 s where the point said 11 s
        price_in, price_out = _price(pid, step.get("model_name") or step.get("model") or "")
        cost = (input_chars / 3.2) * price_in / 1e6 + (out_chars / 3.2) * price_out / 1e6
        step["est"] = {
            "tokens": tokens,
            "tokens_min": tokens,
            "tokens_max": tokens_hi,
            "seconds": round(seconds, 1),
            "seconds_min": seconds_lo,
            "seconds_max": seconds_hi,
            "in": round(input_chars / 3.2),
            "out": round(out_chars / 3.2),
            "cost": round(cost, 6),
            "cost_min": round(cost, 6),
            "cost_max": round(cost * 2.0, 6),
        }
        total_tokens += tokens
        total_tokens_hi += tokens_hi
        total_seconds += seconds
        total_seconds_hi += seconds_hi
        total_seconds_lo += seconds_lo
        total_cost += cost
        total_cost_hi += cost * 2.0
        previous += out_chars
    plan["estimate"] = {
        "tokens": round(total_tokens),
        "tokens_min": round(total_tokens),
        "tokens_max": round(total_tokens_hi),
        "seconds": round(total_seconds),
        "seconds_min": round(total_seconds_lo, 1),
        "seconds_max": round(total_seconds_hi, 1),
        "cost": round(total_cost, 6),
        "cost_min": round(total_cost, 6),
        "cost_max": round(total_cost_hi, 6),
    }
    return plan


def _justify(plans: list[dict]) -> list[dict]:
    """Every variant gets one sentence: what it costs and why next to the most economical one."""
    if not plans:
        return plans
    base = min(plans, key=lambda p: int((p.get("estimate") or {}).get("tokens_min") or 0))
    base_est = base.get("estimate") or {}
    base_steps = len(base.get("steps") or [])
    base_title = base.get("title") or "Быстро"
    for plan in plans:
        est = plan.get("estimate") or {}
        steps = len(plan.get("steps") or [])
        tokens = f"{_tokens_text(est.get('tokens_min') or 0)}–{_tokens_text(est.get('tokens_max') or 0)}"
        money = _money(float(est.get("cost_min") or 0), float(est.get("cost_max") or 0))
        if plan is base:
            plan["why"] = (
                f"Самый экономный по токенам: {steps} {_steps_word(steps)}, {tokens} токенов, {money}. "
                "Чем меньше шагов, тем меньше контекста уходит модели."
            )
            continue
        extra_tokens = max(0, int(est.get("tokens_min") or 0) - int(base_est.get("tokens_min") or 0))
        extra_cost = float(est.get("cost_min") or 0) - float(base_est.get("cost_min") or 0)
        if extra_cost > 0.00005:
            money_part = f" и {_money(extra_cost)}"
            lead = "Дороже"
        elif extra_cost < -0.00005:
            money_part = f", но деньги ниже на {_money(-extra_cost)} за счёт локальных или дешёвых моделей"
            lead = "Больше по токенам"
        else:
            money_part = ", деньги примерно те же"
            lead = "Дороже по токенам"
        plan["why"] = (
            f"{lead} «{base_title}» на ~{_tokens_text(extra_tokens)} токенов{money_part}: "
            f"{steps} {_steps_word(steps)} вместо {base_steps}. Каждый следующий шаг получает ответы "
            "предыдущих, поэтому вход растёт."
        )
    return plans


def _by_cost(rows: list[dict]) -> list[dict]:
    """Cheapest models first: the fallback for a plan that does not fit the budget."""
    return sorted(rows, key=lambda r: sum(_price(r["pid"], r["name"])))


def _fit_budget(plan: dict, rows: list[dict], budget: float, task: str, context_chars: int) -> dict:
    """Keep the scheme inside the budget: the dearest steps drop to the cheapest connected model."""
    estimate(plan, task, context_chars)
    downgraded = False
    cheap = _by_cost(rows)

    def step_price(step: dict) -> float:
        pid = str(step.get("model") or "").split(":", 1)[0]
        return sum(_price(pid, step.get("model_name") or step.get("model") or ""))

    for _ in range(12):
        if float((plan.get("estimate") or {}).get("cost_min") or 0) <= budget + 1e-9:
            break
        steps = plan.get("steps") or []
        order = sorted(
            range(len(steps)), key=lambda i: float((steps[i].get("est") or {}).get("cost_min") or 0), reverse=True
        )
        changed = False
        for i in order:
            step = steps[i]
            current = step_price(step)
            target = next(
                (r for r in cheap if r["model"] != step.get("model") and sum(_price(r["pid"], r["name"])) < current),
                None,
            )
            if not target:
                continue
            step["model"], step["model_name"], step["provider"] = target["model"], target["name"], target["provider"]
            step["downgraded"] = True
            downgraded = True
            changed = True
            estimate(plan, task, context_chars)
            break
        if not changed:
            break
    est = plan.get("estimate") or {}
    plan["budget"] = {
        "usd": round(float(budget), 4),
        "fit": float(est.get("cost_min") or 0) <= budget + 1e-9,
        "min_usd": round(float(est.get("cost_min") or 0), 4),
        "downgraded": downgraded,
    }
    return plan


def recommend_budget(vault: Vault, task: str, context_chars: int = 0, rows: list[dict] | None = None) -> dict:
    """The recommended budget: the cheap «Качественно» estimate plus a margin, so a scheme fits without pressure."""
    task = (task or "").strip()
    if not task:
        return {"usd": 0.05, "cheap_usd": 0.0, "note": "пустая задача — запасной бюджет"}
    plans = fallback_plans(vault, task, context_chars=context_chars, economy=True)
    quality = next((p for p in plans if p.get("id") == "quality"), plans[-1])
    est = quality.get("estimate") or {}
    cheap = float(est.get("cost_min") or 0)
    usd = max(RECOMMEND_MIN, round(float(est.get("cost_max") or cheap) * RECOMMEND_FACTOR, 2))
    return {"usd": usd, "cheap_usd": round(cheap, 4), "note": "смета дешёвой схемы с запасом"}


def _slug(text: str) -> str:
    out = re.sub(r"[^\w\-]+", "-", (text or "").lower(), flags=re.UNICODE).strip("-")
    return out[:48] or "план"


def _save_plan_document(vault: Vault, task: str, plans: list[dict], context: dict, planner: dict | None = None) -> str:
    """A Markdown document with the schema, next to the other notes: the owner asked for a file, not only a card."""
    try:
        folder = vault.root / "00 Inbox" / "Схемы"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y-%m-%d_%H-%M")
        path = folder / f"{stamp}-{_slug(task)}.md"
        lines = [
            "# Схема задачи",
            "",
            f"**Задача:** {task}",
            f"**Создана:** {time.strftime('%d.%m.%Y %H:%M')}",
            f"**Контекст:** память {context.get('memory_chars', 0)} знаков, "
            f"история {context.get('history_msgs', 0)} сообщений",
            f"**Исполнителей подбирал:** {planner.get('name') if planner else '—'}",
            "",
            "",
            "## Варианты",
            "",
        ]
        for plan in plans:
            est = plan.get("estimate") or {}
            lines += [
                f"### {plan.get('title')} — {plan.get('note') or ''}".rstrip(),
                "",
                "| # | роль | модель | токены | время |",
                "|---|---|---|---|---|",
            ]
            for i, step in enumerate(plan.get("steps") or [], 1):
                e = step.get("est") or {}
                lines.append(
                    f"| {i} | {step.get('role') or ''} | {step.get('model_name') or step.get('model') or ''} | "
                    f"{e.get('tokens_min', 0)}–{e.get('tokens_max', 0)} | "
                    f"{e.get('seconds_min', 0)}–{e.get('seconds_max', 0)} с |"
                )
            lines += [
                "",
                f"**Прогноз:** {est.get('tokens_min', 0)}–{est.get('tokens_max', 0)} токенов · "
                f"{est.get('seconds_min', 0)}–{est.get('seconds_max', 0)} с · {_money(est.get('cost_min', 0), est.get('cost_max', 0))}",
                "",
                f"**Почему так:** {plan.get('why') or ''}",
                "",
            ]
        path.write_text("\n".join(lines), encoding="utf-8")
        return str(path)
    except OSError:
        return ""


_STOP_NAMES = {
    "empty_step": "шаг не дал результата",
    "timeout": "превышен лимит времени",
    "owner": "остановлено владельцем",
    "loop": "модель зациклилась на одном действии",
}


def _actions_count(n: int) -> str:
    """How many actions a step made, in human words: «ни одного действия», «1 действие», «3 действия»."""
    if n <= 0:
        return "ни одного действия"
    if 11 <= n % 100 <= 14:
        return f"{n} действий"
    if n % 10 == 1:
        return f"{n} действие"
    if 2 <= n % 10 <= 4:
        return f"{n} действия"
    return f"{n} действий"


def _append_plan_result(vault: Vault, plan: dict) -> None:
    """Put the real step results into the schema document, so the chat can stay compact."""
    raw = str(plan.get("doc") or "")
    if not raw:
        return
    try:
        path = Path(raw).resolve()
        if not path.is_relative_to(vault.root.resolve()):
            return
        actual = plan.get("actual") or {}
        reason = str(plan.get("stop_reason") or "")
        lines = [
            "",
            "## Результат",
            "",
            f"**Задача:** {plan.get('task') or '—'}",
            f"**Статус:** {plan.get('status')} · {len(plan.get('steps') or [])} шагов · "
            f"{actual.get('seconds', '—')} с · {actual.get('tokens', '—')} токенов",
        ]
        if reason:
            lines.append(f"**Причина остановки (stop_reason):** {reason} — {_STOP_NAMES.get(reason, reason)}")
        lines.append("")
        for i, step in enumerate(plan.get("steps") or [], 1):
            head = f"### Шаг {i} · {step.get('role') or ''} · {step.get('model_name') or ''}"
            if step.get("status") or "actions" in step:
                head += f" — статус: {step.get('status') or '—'}, действий: {int(step.get('actions') or 0)}"
            lines += [head, ""]
            if step.get("note"):
                lines += [f"**Что случилось:** {step['note']}", ""]
            lines += [str(step.get("output") or "—"), ""]
        path.write_text(path.read_text(encoding="utf-8") + "\n".join(lines), encoding="utf-8")
    except (OSError, ValueError):
        pass


def _step(rows: list[dict], used: set[str], role: str, out: str, instruction: str, want: int = 2) -> dict | None:
    row = _pick(rows, want, used)
    if not row:
        return None
    used.add(row["model"])
    return {
        "role": role,
        "out": out,
        "instruction": instruction,
        "model": row["model"],
        "model_name": row["name"],
        "provider": row["provider"],
    }


def fallback_plans(vault: Vault, task: str, context_chars: int = 0, economy: bool = True) -> list[dict]:
    """Three ready schemes. Economy (on by default) takes cheap executors and splits the work into simple
    self-contained steps; the strong tier is used only when the owner switched economy off."""
    rows = available(vault)
    if not rows:
        raise ValueError("нет подключённых моделей: подключи хотя бы одну в Настройках → ИИ и модели")
    cheap = 1 if economy else 2
    quality_wants = [1, 1, 1, 1, 1] if economy else [3, 3, 2, 3, 2]
    used: set[str] = set()
    fast = [_step(rows, used, "Ответ", "ответ", "Реши задачу сразу, по существу, без плана и черновиков.", want=1)]
    used.clear()
    balanced = [
        _step(
            rows, used, "Разбор", "план", "Разбей задачу на 2–4 простые подзадачи и верни только их список.", want=cheap
        ),
        _step(
            rows,
            used,
            "Черновик",
            "черновик",
            "Сделай черновик результата по списку подзадач. Работай только по списку, не пересказывай задачу.",
            want=cheap,
        ),
        _step(
            rows,
            used,
            "Проверка",
            "критика",
            "Проверь черновик: ошибки, пропуски, ясность. Верни короткий список правок.",
            want=cheap if economy else 2,
        ),
    ]
    used.clear()
    quality = [
        _step(
            rows,
            used,
            "Разбор",
            "план",
            "Разбей задачу на 3–5 простых подзадач и верни только их список.",
            want=quality_wants[0],
        ),
        _step(
            rows,
            used,
            "Черновик",
            "черновик",
            "Сделай черновик результата по списку подзадач. Работай только по списку.",
            want=quality_wants[1],
        ),
        _step(
            rows,
            used,
            "Критик",
            "критика",
            "Проверь черновик: ошибки, пропуски, ясность. Верни короткий список правок.",
            want=quality_wants[2],
        ),
        _step(
            rows,
            used,
            "Правки",
            "черновик",
            "Внеси правки в черновик и верни исправленный текст целиком.",
            want=quality_wants[3],
        ),
        _step(
            rows,
            used,
            "Финал",
            "финал",
            "Сократи и отредактируй до финального ответа, сохранив смысл.",
            want=quality_wants[4],
        ),
    ]
    plans = [
        {"id": "fast", "title": "Быстро", "note": "Один сильный ответ, минимум времени", "steps": fast},
        {"id": "optimal", "title": "Оптимально", "note": "Простой разбор → работа → проверка", "steps": balanced},
        {"id": "quality", "title": "Качественно", "note": "Простые шаги, ИИ дорабатывают друг друга", "steps": quality},
    ]
    return _justify([estimate(p, task, context_chars=context_chars) for p in plans if p["steps"]])


PLAN_PROMPT = """Ты — планировщик цепочки ИИ. Владелец даст задачу, а ты разложи её на шаги и подбери исполнителей
строго из списка доступных моделей. Верни ТОЛЬКО JSON, без пояснений:

{"plans":[{"title":"Быстро","note":"...","steps":[{"role":"...","instruction":"...","model":"pid:model","out":"ответ"}]},
{"title":"Оптимально",...},{"title":"Качественно",...}]}

Правила: 3 плана — «Быстро» 1–2 шага, «Оптимально» 3 шага, «Качественно» 4–5 шагов. Роли разные, инструкции
короткие и конкретные, модель — точная строка вида pid:model из списка. out — одно из: короткий, план, черновик,
критика, финал, ответ. Никакого markdown вокруг JSON."""


def _parse_plans(text: str, rows: list[dict]) -> list[dict]:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return []
    allowed = {r["model"]: r for r in rows}
    plans = []
    for raw in (data.get("plans") or [])[:3]:
        steps = []
        for s in (raw.get("steps") or [])[:MAX_STEPS]:
            model = str(s.get("model") or "")
            if model not in allowed:
                continue
            steps.append(
                {
                    "role": str(s.get("role") or "Шаг")[:40],
                    "instruction": str(s.get("instruction") or "")[:500],
                    "out": str(s.get("out") or "ответ"),
                    "model": model,
                    "model_name": allowed[model]["name"],
                    "provider": allowed[model]["provider"],
                }
            )
        if steps:
            plans.append(
                {"title": str(raw.get("title") or "План")[:24], "note": str(raw.get("note") or "")[:80], "steps": steps}
            )
    return plans


def propose(
    vault: Vault,
    task: str,
    chat_id: str = "",
    planner: str = "auto",
    budget: float | None = None,
    economy: bool = True,
) -> list[dict]:
    """Ask a cheap connected AI to choose the roles and executors; fall back to the built-in schemes.

    economy (on by default) asks for cheap executors and simple self-contained steps, and every offered
    variant is fitted into the budget (a custom one, or the recommended cheap estimate plus a margin).
    """
    task = (task or "").strip()
    if not task:
        raise ValueError("напиши задачу")
    rows = available(vault)
    if not rows:
        raise ValueError("нет подключённых моделей: подключи хотя бы одну в Настройках → ИИ и модели")
    recommended = recommend_budget(vault, task, rows=rows)["usd"]
    budget_usd = round(float(budget), 4) if budget is not None else recommended
    if budget_usd <= 0:
        raise ValueError("бюджет должен быть больше нуля")
    plans: list[dict] = []
    chosen = _planner(rows, planner)
    memory = _memory(vault, chosen["pid"])
    history = _history(vault, chat_id)
    context_chars = min(len(memory), 8000) + sum(len(line) for line in history)
    context_info = {
        "memory_chars": len(memory),
        "history_msgs": len(history),
        "history_chars": sum(len(line) for line in history),
    }
    try:
        pid, mname = CH.split_model(chosen["model"])
        listing = "\n".join(f"- {r['model']} — {r['name']} ({r['provider']})" for r in rows[:40])
        system = PLAN_PROMPT
        system += f"\n\nБюджет схемы: не более ${budget_usd:.2f}. Смета каждого варианта — не больше бюджета."
        if economy:
            system += (
                "\nЭкономия включена: дроби задачу на простые самодостаточные шаги. Каждый шаг — понятная задача "
                "с явными входами и выходами; исполнителю не нужна история разговора, только переданные данные. "
                "Бери дешёвые модели (harness, deepseek, локальные); дорогую модель — только если шаг окупается "
                "и это заметно повышает качество, не больше одного-двух таких шагов."
            )
        else:
            system += "\nЭкономия выключена: можно брать сильные модели, если это оправдано качеством."
        if memory:
            system += (
                "\n\nПамять о владельце (кто он, его правила, проекты — учитывай при выборе шагов):\n" + memory[-8000:]
            )
        if history:
            system += "\n\nПоследние сообщения разговора:\n" + "\n".join(history)
        system += "\n\nДоступные модели:\n" + listing
        usage: dict = {}
        answer = PR.complete(
            vault,
            pid,
            mname,
            system,
            [{"role": "user", "text": "Задача владельца:\n" + task}],
            usage=usage,
            meta={"purpose": "план задачи"},
        )
        plans = _parse_plans(answer, rows)
    except Exception:  # noqa: BLE001 — a plan must always be offered, even if the planner model is down
        plans = []
    if len(plans) < 3:
        plans = (plans + fallback_plans(vault, task, context_chars=context_chars, economy=economy))[:3]
    ids = ["fast", "optimal", "quality"]
    for i, p in enumerate(plans):
        p["id"] = ids[i] if i < len(ids) else f"plan{i}"
        p.setdefault("note", "")
        p["context"] = context_info
        p["economy"] = economy
        estimate(p, task, context_chars=context_chars)
        _fit_budget(p, rows, budget_usd, task, context_chars)
        p["budget"]["recommended"] = recommended
    result = _justify(plans)
    # a read-only MCP sweep must not leave even a scheme document in the vault
    doc = "" if _is_mcp_readonly_sweep(task) else _save_plan_document(vault, task, result, context_info, chosen)
    if doc:
        for p in result:
            p["doc"] = doc
    for p in result:
        p["planner"] = {"model": chosen["model"], "name": chosen["name"], "provider": chosen["provider"]}
    return result


_UNFINISHED = re.compile(
    r"продолж|сейчас (?:вызов|провер|запущ)|дальше|next|to be continued|осталось|ещё не|not finished",
    re.I,
)


def _prompt_for(plan: dict, index: int, task: str, previous: list[str]) -> str:
    prev = "\n\n".join(f"[Шаг {i + 1} — {plan['steps'][i]['role']}]\n{text}" for i, text in enumerate(previous))
    prev = prev[-12000:] if len(prev) > 12000 else prev
    step = plan["steps"][index]
    return (
        f"Задача владельца:\n{task}\n\n"
        + (f"Что уже сделано:\n{prev}\n\n" if prev else "")
        + f"Твой шаг ({index + 1} из {len(plan['steps'])}), роль «{step['role']}»:\n{step['instruction']}\n\n"
        "Верни только результат этого шага, без отчёта о процессе."
    )


# the one extra call after a tool-using step that forgot to sum up: tools are forbidden outright
SUMMARY_ASK = "Инструменты уже выполнены, не вызывай их снова; сформулируй краткий итог шага по полученным результатам."
TOOLS_FORBIDDEN = "Инструменты на этом вызове запрещены: не вызывай их, верни только текст итога шага."


def _stop_text(plan: dict, steps: list[dict], index: int, reason: str) -> str:
    """Why the chain stopped and what the owner can do — the concrete cause, never a bare «шаг не дал текста»."""
    total = len(steps)
    step = steps[index] if 0 <= index < total else {}
    role = step.get("role") or "шаг"
    where = f"шаге {index + 1} из {total} — «{role}»"
    advice = (
        "Открой документ схемы (кнопка «Документ»), чтобы увидеть, что успели сделать предыдущие шаги, "
        "или пересобери схему и выбери для этого шага другую модель."
        if plan.get("doc")
        else "Пересобери схему и выбери для этого шага другую модель."
    )
    if reason == "owner":
        return f"Остановлено владельцем на {where}. {advice}"
    if reason == "loop":
        note = str(step.get("note") or "").rstrip(".")
        return f"План остановлен на {where}: {note}. Следующие шаги не запускались. {advice}"
    if reason == "timeout":
        note = str(step.get("note") or "").rstrip(".")
        return f"План остановлен по лимиту времени на {where}: {note}. {advice}"
    actions = int(step.get("actions") or 0)
    what = (
        "модель не вызвала инструменты и не вернула текст"
        if actions <= 0
        else f"модель сделала {_actions_count(actions)}, но не сформулировала итог"
    )
    return f"План остановлен на {where}: {what}, поэтому следующие шаги не запускались. {advice}"


def _is_mcp_readonly_sweep(task: str) -> bool:
    """The owner asks for the whole MCP catalog with a strictly read-only vault."""
    t = (task or "").lower()
    readonly = any(
        marker in t
        for marker in ("только чита", "ничего не записывай", "не записывай в память", "read-only", "readonly")
    )
    return (
        readonly
        and "mcp" in t
        and any(marker in t for marker in ("tools/list", "все инструменты", "всех инструментов", "каждый инструмент"))
    )


def _fallback_row(vault: Vault, failed_pid: str):
    """If a paid provider refuses (402) or is down, finish the step on a connected local/harness model."""
    try:
        rows = [r for r in available(vault) if str(r.get("pid")) != failed_pid]
    except Exception:  # noqa: BLE001 — no fallback is not a reason to fail differently
        return None
    if not rows:
        return None
    rows.sort(key=lambda r: 0 if r.get("pid") == "harness" else 1 if r.get("pid") == "local" else 2)
    return rows[0]


def _progress(plan: dict, steps: list[dict], current: int = -1) -> dict:
    """A small snapshot for the live plan card: statuses only, never full step outputs."""
    rows = []
    for i, step in enumerate(steps):
        status = step.get("status")
        if not status:
            status = "running" if i == current else "pending"
        rows.append(
            {
                "role": step.get("role"),
                "model_name": step.get("model_name"),
                "status": status,
                "actions": int(step.get("actions") or 0),
                "actual": step.get("actual"),
                "est": step.get("est"),
                "note": step.get("note"),
            }
        )
    return {
        "id": plan.get("id"),
        "title": plan.get("title"),
        "note": plan.get("note"),
        "task": plan.get("task"),
        "doc": plan.get("doc"),
        "estimate": plan.get("estimate"),
        "context": plan.get("context"),
        "status": plan.get("status"),
        "stop_reason": plan.get("stop_reason"),
        "steps": rows,
    }


def _live_text(steps: list[dict], current: int = -1) -> str:
    """What the owner sees while the chain runs: finished steps and the current one, not a wall of answers."""
    lines = []
    for i, step in enumerate(steps):
        status = step.get("status")
        actual = step.get("actual") or {}
        if status == "ok":
            lines.append(f"✓ Шаг {i + 1} · {step.get('role') or ''} · {actual.get('seconds', '—')} с")
        elif status in ("empty", "timeout"):
            lines.append(f"✗ Шаг {i + 1} · {step.get('role') or ''} — {step.get('note') or status}")
        elif status == "stopped":
            lines.append(f"· Шаг {i + 1} · {step.get('role') or ''} — не выполнялся")
    if 0 <= current < len(steps):
        step = steps[current]
        lines.append(f"**Шаг {current + 1} из {len(steps)} · {step.get('role') or ''}**\nвыполняется…")
    return "\n\n".join(lines)


def run(vault: Vault, cid: str, plan: dict) -> dict:
    """Start the chosen chain in a chat: each step is one AI call, the results are passed on to the next."""
    task = str(plan.get("task") or "").strip()
    steps = plan.get("steps") or []
    if not steps:
        raise ValueError("в плане нет шагов")
    allowed = {r["model"] for r in available(vault)}
    for s in steps:
        if s.get("model") not in allowed:
            raise ValueError("модель шага больше не подключена")
    if not cid:
        raise ValueError("план запускается в разговоре")
    plan = json.loads(json.dumps(plan))
    steps = plan["steps"]  # the copy, not the request object: outputs must be saved in the plan message
    plan.pop("stop_reason", None)  # a re-run of a stopped plan starts clean
    for s in steps:
        for key in ("status", "note", "actions", "actual", "output", "empty"):
            s.pop(key, None)
        s["status"] = "pending"
    plan["task"] = task
    plan["status"] = "running"
    first_pid = CH.split_model(steps[0]["model"])[0]
    memory = _memory(vault, first_pid)
    history = _history(vault, cid)
    context_chars = min(len(memory), 8000) + sum(len(line) for line in history)
    plan["context"] = {
        "memory_chars": len(memory),
        "history_msgs": len(history),
        "history_chars": sum(len(line) for line in history),
    }
    estimate(plan, task, context_chars=context_chars)
    mid = secrets.token_hex(4)
    CH._add_msg(
        vault,
        cid,
        {"role": "assistant", "kind": "plan", "id": mid, "ts": CH._now(), "plan": plan, "text": ""},
    )
    g = {
        "text": "",
        "done": False,
        "error": "",
        "phase": "готовлю цепочку",
        "started": time.time(),
        "stop": False,
        "pid": "plan",
        "who": "",
    }
    CH._gen[cid] = g
    g["plan_progress"] = _progress(plan, steps, 0)
    g["text"] = _live_text(steps, 0)

    def work():
        made: list[str] = []
        tokens = 0
        actions_total = 0
        stop_reason = ""
        stop_at = -1  # the 0-based step the chain stopped on, for an honest report
        started = time.time()
        try:
            from . import tools as TL

            tools_on = TL.enabled(vault)
            tool_rule = TL.rule(vault) if tools_on else ""
            for i, step in enumerate(steps):
                step["actions"] = 0
                if g["stop"]:
                    stop_reason, stop_at = "owner", i
                    step["status"] = "stopped"
                    step["note"] = "не выполнялся: остановлено владельцем"
                    break
                step_started = time.time()
                step_usage: dict = {}
                step["status"] = "running"
                g["plan_progress"] = _progress(plan, steps, i)
                g["text"] = _live_text(steps, i)
                g["phase"] = f"шаг {i + 1} из {len(steps)}: {step['role']}"
                pid, mname = CH.split_model(step["model"])
                client = PR.PROVIDERS[pid]["client"]
                fallback = _fallback_row(vault, pid)
                system = (
                    f"Ты — исполнитель шага {i + 1} из {len(steps)} в цепочке ИИ. Твоя роль: {step['role']}. "
                    "Работай только над своим шагом, не повторяй работу предыдущих и верни его результат."
                )
                if tools_on:
                    system += (
                        "\n\nЕсли для шага нужны инструменты, вызывай их действиями Mnemai. Не выдумывай "
                        "результаты инструментов: настоящий результат придёт тебе следующим сообщением. "
                        "MCP-инструменты Mnemai вызывай блоком ```mnema mcp_call name=\"имя\"``` с JSON-аргументами "
                        "в теле (например memory_context, pc_run, web_search); tools/list — это MCP-метод, "
                        "а не shell-команда. Для задачи «проверить все инструменты MCP» используй один блок "
                        "```mnema mcp_smoke```: он сам проходит весь каталог, составляет таблицу и убирает следы.\n\n"
                        + tool_rule
                    )
                step_memory = _memory(vault, pid)
                user = ""
                if step_memory:
                    user += "Память о владельце (используй, если относится к делу):\n" + step_memory[:8000] + "\n\n"
                if history:
                    user += "Последние сообщения разговора:\n" + "\n".join(history) + "\n\n"
                user += _prompt_for(plan, i, task, made)
                messages = [{"role": "user", "text": user}]
                answer = ""
                step_actions = 0
                last_sig = ""
                same_action = 0
                for attempt in range(2):
                    if g["stop"]:
                        break
                    for _round in range(12):  # many MCP calls in a row, still bounded
                        if g["stop"]:
                            break
                        try:
                            call_started = time.monotonic()
                            raw = PR.complete(
                                vault,
                                pid,
                                mname,
                                system,
                                messages,
                                usage=step_usage,
                                meta={"purpose": f"шаг плана {i + 1}", "chat": cid},
                                stop=lambda: g["stop"] or time.monotonic() - call_started > PROVIDER_SECONDS,
                            )
                        except Exception as e:  # noqa: BLE001 — a paid provider may answer 402/500
                            if fallback is None:
                                raise
                            old = f"{pid}:{mname}"
                            pid, mname = CH.split_model(str(fallback["model"]))
                            client = PR.PROVIDERS[pid]["client"]
                            step["fallback"] = f"{old} → {pid}:{mname}: {type(e).__name__}: {str(e)[:160]}"
                            g["phase"] = f"шаг {i + 1}: провайдер не ответил, продолжаю на {mname}"
                            fallback = None
                            continue
                        clean = CH.strip_thinking(raw)
                        call = TL.parse(clean) if tools_on else None
                        if call:
                            actions_total += 1
                            step_actions += 1
                            if actions_total > 80:  # a model stuck in a tool loop must not take the app down
                                answer = "Слишком много действий подряд — шаг остановлен. Уточни задачу."
                                break
                            sig = json.dumps(
                                [
                                    call.get("tool"),
                                    call.get("name"),
                                    call.get("args"),
                                    call.get("command"),
                                    call.get("body"),
                                ],
                                ensure_ascii=False,
                                sort_keys=True,
                            )
                            if sig == last_sig:
                                same_action += 1
                            else:
                                last_sig, same_action = sig, 1
                            if same_action >= 3:
                                stop_reason, stop_at = "loop", i
                                label = call.get("name") or call.get("tool")
                                step["note"] = f"модель три раза подряд попросила «{label}» и не двигалась дальше"
                                answer = step["note"]
                                break
                            said = TL.before(clean, call)
                            result = CH._act(vault, cid, g, call, client, step["model"])
                            if result is None:
                                g["stop"] = True
                                break
                            if said.strip():
                                messages.append({"role": "assistant", "text": said.strip()})
                            messages.append(
                                {"role": "user", "text": "[Результат действия Mnemai]\n" + str(result)[:3500]}
                            )
                            continue
                        answer = CH.strip_tool_markup(clean).strip()
                        if answer and step_actions and _round < 7 and (len(answer) < 180 or _UNFINISHED.search(answer)):
                            # a model often says «продолжаю» after one tool and calls it a finished step
                            messages.append({"role": "assistant", "text": answer})
                            messages.append(
                                {
                                    "role": "user",
                                    "text": "Это ещё не итог шага: выполни оставшиеся пункты задания, вызови нужные "
                                    "инструменты и верни только итоговый отчёт.",
                                }
                            )
                            answer = ""
                            continue
                        break
                    if answer or g["stop"]:
                        break
                    if step_actions:
                        break  # it already used tools: another blind round would only burn time and tokens
                    messages.append(
                        {"role": "user", "text": "Ты не вернул результат шага. Выполни его и верни текст результата."}
                    )
                step["actions"] = step_actions
                if not answer.strip() and step_actions and not g["stop"]:
                    # tools were used but the model never summed up: one last call that is not allowed to act
                    g["phase"] = f"шаг {i + 1}: прошу итог без инструментов"
                    try:
                        raw = PR.complete(
                            vault,
                            pid,
                            mname,
                            system + "\n\n" + TOOLS_FORBIDDEN,
                            messages + [{"role": "user", "text": SUMMARY_ASK}],
                            usage=step_usage,
                            meta={"purpose": f"итог шага плана {i + 1}", "chat": cid},
                        )
                        answer = CH.strip_tool_markup(CH.strip_thinking(raw)).strip()
                    except Exception:  # noqa: BLE001 — the summary is a courtesy, never a reason to lose the plan
                        answer = ""
                step_seconds = round(time.time() - step_started, 1)
                step_tokens = sum(int(val) for val in step_usage.values() if isinstance(val, (int, float)))
                tokens += step_tokens
                step["actual"] = {"tokens": step_tokens, "seconds": step_seconds}
                step["output"] = answer
                if g["stop"]:
                    stop_reason, stop_at = "owner", i
                    step["status"] = "stopped"
                    step["note"] = "остановлено владельцем на этом шаге"
                elif stop_reason == "loop":
                    stop_reason, stop_at = "loop", i
                    step["status"] = "stopped"
                elif not answer.strip():
                    stop_reason, stop_at = "empty_step", i
                    step["status"] = "empty"
                    step["note"] = (
                        f"модель сделала {_actions_count(step_actions)}, но не сформулировала итог"
                        if step_actions
                        else "модель не вернула текст, хотя инструменты не вызывались"
                    )
                else:
                    step["status"] = "ok"
                    step["note"] = ""
                made.append(answer)
                g["plan_progress"] = _progress(plan, steps)
                g["text"] = _live_text(steps)
                try:
                    CH._update_msg(vault, cid, mid, {"plan": plan})  # switching back mid-run shows the statuses
                except Exception:  # noqa: BLE001 — a progress write must never break the plan
                    pass
                if stop_reason:
                    break
            g["phase"] = "собираю итог"  # the last step is done; the result card is being written
            if stop_at >= 0:
                for later in steps[stop_at + 1 :]:
                    later["status"] = "stopped"
                    later["note"] = f"не выполнялся: план остановлен на шаге {stop_at + 1}"
            plan["status"] = "stopped" if stop_reason else "done"
            if stop_reason:
                plan["stop_reason"] = stop_reason
            plan["actual"] = {"seconds": round(time.time() - started, 1), "tokens": tokens}
            g["plan_progress"] = _progress(plan, steps)
            _append_plan_result(vault, plan)
            CH._update_msg(vault, cid, mid, {"plan": plan})
            outputs = [str(s.get("output") or "") for s in steps]
            final = next((o for o in reversed(outputs) if o), "")
            if stop_reason:
                cause = _stop_text(plan, steps, stop_at, stop_reason)
                final = cause + (("\n\n" + final) if final.strip() else "")
            if not final.strip():
                final = "План завершён, но ни один шаг не вернул текст. Открой документ схемы, чтобы увидеть детали."
            CH._add_msg(
                vault,
                cid,
                {
                    "role": "assistant",
                    "kind": "plan_result",
                    "text": final.strip(),
                    "ts": CH._now(),
                    "model": "plan",
                    "plan": {
                        "title": plan.get("title"),
                        "task": task,
                        "steps": len(steps),
                        "doc": plan.get("doc"),
                        "status": plan.get("status"),
                        "stop_reason": plan.get("stop_reason"),
                    },
                },
            )
        except Exception as e:  # noqa: BLE001 — the chat always ends honestly
            g["error"] = f"План остановлен: {type(e).__name__}: {str(e)[:200]}"
            plan["status"] = "failed"
            try:
                _append_plan_result(vault, plan)
                CH._update_msg(vault, cid, mid, {"plan": plan})
            except Exception:
                pass
        finally:
            g["phase"] = ""
            g["done"] = True
            try:
                CH._drain_queue(vault, cid)  # a correction typed during the chain becomes the next turn
            except Exception:  # noqa: BLE001 — the queue is a bonus, never a reason to lose the chat
                pass

    threading.Thread(target=work, daemon=True, name="mnema-plan").start()
    return {"chat": cid, "plan": plan}
