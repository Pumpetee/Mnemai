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

from ..vault import Vault
from . import engine as CH, providers as PR

MAX_STEPS = 6
FREE = {"local", "ollama", "strata"}  # runs on this computer: no token price
STRONG = {"claude_code", "anthropic", "openai", "gemini", "openrouter", "codex"}
OUT_CHARS = {"короткий": 700, "план": 1200, "черновик": 3500, "критика": 1000, "финал": 2200, "ответ": 1500}
SPEED = {"local": 40.0, "ollama": 45.0, "strata": 60.0}  # chars per second on this computer
CLOUD_SPEED = 220.0  # chars per second of cloud streaming, a rough but honest order of magnitude


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


def _pick(rows: list[dict], want: int, used: set[str]) -> dict | None:
    for row in rows:
        if row["tier"] == want and row["model"] not in used:
            return row
    for row in rows:
        if row["model"] not in used:
            return row
    return rows[0] if rows else None


def _est_chars(text: str) -> int:
    return max(1, int(len(text or "") * 1.1))


def estimate(plan: dict, task: str) -> dict:
    """Where the numbers come from: input chars of task+previous answers+instruction, output by role, speed by provider."""
    previous = 0
    total_tokens = total_seconds = 0.0
    for step in plan.get("steps") or []:
        instruction = str(step.get("instruction") or "")
        input_chars = 500 + _est_chars(task) + previous + _est_chars(instruction)
        out_chars = OUT_CHARS.get(str(step.get("out") or "ответ"), 1500)
        pid = str(step.get("model") or "").split(":", 1)[0]
        speed = SPEED.get(pid, CLOUD_SPEED)
        seconds = 2.5 + out_chars / speed + 1.2
        tokens = round(input_chars / 3.2 + out_chars / 3.2)
        step["est"] = {
            "tokens": tokens,
            "seconds": round(seconds, 1),
            "in": round(input_chars / 3.2),
            "out": round(out_chars / 3.2),
        }
        total_tokens += tokens
        total_seconds += seconds
        previous += out_chars
    plan["estimate"] = {"tokens": round(total_tokens), "seconds": round(total_seconds)}
    return plan


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


def fallback_plans(vault: Vault, task: str) -> list[dict]:
    rows = available(vault)
    if not rows:
        raise ValueError("нет подключённых моделей: подключи хотя бы одну в Настройках → ИИ и модели")
    used: set[str] = set()
    fast = [_step(rows, used, "Ответ", "ответ", "Реши задачу сразу, по существу, без плана и черновиков.", want=1)]
    used.clear()
    balanced = [
        _step(rows, used, "План", "план", "Разложи задачу на шаги и реши, что должно быть в результате.", want=2),
        _step(rows, used, "Черновик", "черновик", "Сделай работу по плану предыдущего шага.", want=3),
        _step(
            rows,
            used,
            "Проверка",
            "критика",
            "Проверь черновик: ошибки, пропуски, ясность. Дай короткий список правок.",
            want=2,
        ),
    ]
    used.clear()
    quality = [
        _step(rows, used, "Исследование", "план", "Собери факты и составь точный план результата.", want=3),
        _step(rows, used, "Черновик", "черновик", "Сделай полный черновик по плану.", want=3),
        _step(rows, used, "Критик", "критика", "Найди слабые места и конкретные улучшения, без переписывания.", want=2),
        _step(rows, used, "Доработка", "черновик", "Внеси правки критика и усиль результат.", want=3),
        _step(rows, used, "Финал", "финал", "Отредактируй до финального ответа: ясно, коротко, без потерь.", want=2),
    ]
    plans = [
        {"id": "fast", "title": "Быстро", "note": "Один сильный ответ, минимум времени", "steps": fast},
        {"id": "optimal", "title": "Оптимально", "note": "План → работа → проверка", "steps": balanced},
        {"id": "quality", "title": "Качественно", "note": "Несколько ИИ дорабатывают друг друга", "steps": quality},
    ]
    return [estimate(p, task) for p in plans if p["steps"]]


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


def propose(vault: Vault, task: str) -> list[dict]:
    """Ask a cheap connected AI to choose the roles and executors; fall back to the built-in schemes."""
    task = (task or "").strip()
    if not task:
        raise ValueError("напиши задачу")
    rows = available(vault)
    if not rows:
        raise ValueError("нет подключённых моделей: подключи хотя бы одну в Настройках → ИИ и модели")
    plans: list[dict] = []
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
    cheapest = next((r for pid_ in order for r in rows if r["pid"] == pid_), rows[0])
    try:
        pid, mname = CH.split_model(cheapest["model"])
        listing = "\n".join(f"- {r['model']} — {r['name']} ({r['provider']})" for r in rows[:40])
        system = PLAN_PROMPT + "\n\nДоступные модели:\n" + listing
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
        plans = (plans + fallback_plans(vault, task))[:3]
    ids = ["fast", "optimal", "quality"]
    for i, p in enumerate(plans):
        p["id"] = ids[i] if i < len(ids) else f"plan{i}"
        p.setdefault("note", "")
        estimate(p, task)
    return plans


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
    plan["task"] = task
    plan["status"] = "running"
    estimate(plan, task)
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

    def work():
        made: list[str] = []
        tokens = 0
        started = time.time()
        try:
            for i, step in enumerate(steps):
                if g["stop"]:
                    g["text"] += "\n\n_Остановлено владельцем._"
                    break
                step_started = time.time()
                step_usage: dict = {}
                g["phase"] = f"шаг {i + 1} из {len(steps)}: {step['role']}"
                pid, mname = CH.split_model(step["model"])
                system = (
                    f"Ты — исполнитель шага {i + 1} из {len(steps)} в цепочке ИИ. Твоя роль: {step['role']}. "
                    "Работай только над своим шагом и верни его результат."
                )
                try:
                    answer = PR.complete(
                        vault,
                        pid,
                        mname,
                        system,
                        [{"role": "user", "text": _prompt_for(plan, i, task, made)}],
                        usage=step_usage,
                        meta={"purpose": f"шаг плана {i + 1}", "chat": cid},
                    ).strip()
                except Exception as e:  # noqa: BLE001 — one broken step must not lose the whole chain
                    answer = f"_(шаг не выполнен: {type(e).__name__}: {str(e)[:160]})_"
                step_tokens = sum(int(val) for val in step_usage.values() if isinstance(val, (int, float)))
                tokens += step_tokens
                step["actual"] = {"tokens": step_tokens, "seconds": round(time.time() - step_started, 1)}
                made.append(answer)
                g["text"] += f"### Шаг {i + 1} · {step['role']} · {step['model_name']}\n\n{answer.strip()}\n\n"
            plan["status"] = "done" if not g["stop"] else "stopped"
            plan["actual"] = {"seconds": round(time.time() - started, 1), "tokens": tokens}
            CH._update_msg(vault, cid, mid, {"plan": plan})
            if made:
                CH._add_msg(
                    vault,
                    cid,
                    {
                        "role": "assistant",
                        "text": g["text"].strip(),
                        "ts": CH._now(),
                        "model": "plan",
                    },
                )
        except Exception as e:  # noqa: BLE001 — the chat always ends honestly
            g["error"] = f"План остановлен: {type(e).__name__}: {str(e)[:200]}"
            plan["status"] = "failed"
            try:
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
