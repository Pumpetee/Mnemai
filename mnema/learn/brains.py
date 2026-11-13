"""Brains: who reads the owner's texts and pulls out what's worth remembering.

- none        — no model. Explicit signals only: "запомни…", corrections ("нет, не так", "я же говорил"),
                decisions ("решил…"), facts with a status date. Works everywhere, learns little.
- claude_code — the Claude Code already installed (subscription), run headless without tools, hooks or MCP.
- api         — the owner's own key: Anthropic or any OpenAI-compatible endpoint.
- ollama      — a local model, nothing leaves the computer.

Every brain returns candidates in one format:
  {text, kind, where, key, tags, confidence, evidence, contradicts, ref, source}
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from .. import net
from .sources import BRAIN_MARK, Episode

KINDS = {"fact", "rule", "decision", "project", "person", "preference"}

# What is truly personal. A word alone is not enough: «аудитория — молодые семьи, средний доход» is a market
# description, not the owner's money or family, and must not be hidden from AIs or put into a hidden card.
SENSITIVE = {
    "money": (
        r"(?:₽|€|\$|рубл|доллар|евро|\b(?:тыс|млн|миллион|миллиард)\b|"
        r"\d[\d\s.,]{2,}\s*(?:руб|₽|тыс|млн|доллар|евро|€|\$))"
        r"|(?:\b(?:мой|моя|моё|мои|наш|наша|наше|у меня|мне)\b[^.?!]{0,60}"
        r"\b(?:доход|зарплат|кредит|долг|ипотек|сбережен|инвестиц|накоплен|трат|расход|бюджет|подписк|плат))"
        r"|(?:\b(?:зарплат|кредит|долг|ипотек|сбережен)\w*)"
        r"|(?:\b(?:доход|бюджет|подписк|тариф|выручк)\w*\b[^.?!]{0,20}\d)"
        r"|(?:salary|income|debt|\bmy budget\b)"
    ),
    "health": r"здоров|врач|диагноз|болит|болезн|таблет|лекарств|анализ|давлени|бессонниц|депресс|терапи|health|doctor",
    "private": (
        r"жена|муж\b|супруг|развод|(?:\b(?:мой|моя|мои|наша|наши)\b[^.?!]{0,30}\b(?:семь|ребён|дет|родител))|"
        r"интим|любовн|(?:\b(?:сын|дочь|ребёнок)\b)|wife|husband|divorce"
    ),
}

# A task instruction («в этом задании сначала уточняй») is not a rule for every future conversation: a rule needs
# an explicit "always/never" or a correction of the AI. Otherwise the candidate waits for a repeat like a weak fact.
RULE_MARK = re.compile(
    r"\b(?:всегда|никогда|при любом|при любых|правило|не делай|не пиши|не говори|не используй|"
    r"обязательно|запомни как правило)\b",
    re.I,
)

PROMPT = """{mark}
Ты — модуль обучения личной памяти. Ниже реплики владельца памяти из его разговоров, писем и заметок.
Вытащи только то, что стоит помнить о нём надолго и что пригодится любому ИИ, который с ним работает.

Бери:
- факты о нём: кто он, чем занят, где живёт, его проекты и их статусы, люди вокруг и кто они;
- его решения ("решил", "выбираю", "договорились");
- правила работы с ним — особенно из ПОПРАВОК: если он поправляет ИИ ("нет, не так", "я же говорил",
  "не делай", "всегда"), запиши правило, которое предотвратило бы ошибку, повелительно и коротко;
- предпочтения: стиль, форматы, что любит и не терпит;
- ОТВЕТЫ ИИ (поле ai_before): если владелец соглашается с предложением ИИ ("да, так и сделаем", "давай",
  "ок, берём") — это его решение, запиши, что именно решено, по тексту ИИ; если владелец поправляет факт о себе,
  который ИИ назвал ("это уже не так", "я уже не там работаю") — это обновление факта, укажи contradicts.

Не бери: разовые задачи и технические детали текущей работы, содержимое кода, чужие тексты, догадки,
всё, что сказал ИИ, а не владелец. Не выдумывай: каждый пункт подтверждён цитатой (evidence).
Если факт уже есть в списке известного — не повторяй, если противоречит известному — укажи contradicts.
Если в тексте есть дата статуса — сохрани её в формате "(статус ДД.ММ.ГГГГ)".
Куда класть (where): факт о проекте — project:<Название>; о человеке — person:<Имя>; правило работы с ним — rules;
решение — decisions; остальное о его жизни и делах — в карточку темы card:<Тема> (одна тема — одна карточка:
"Работа", "Здоровье", "Семья", "Финансы", "Хобби" и т.п.). Если подходящая карточка уже есть в списке КАРТОЧКИ —
пиши в неё, новую тему заводи, только если ни одна не подходит. inbox — только если непонятно, куда.
Смена статуса проекта — where project:<Название>, text "Статус: active|paused|closed".
Цель проекта, дедлайн или срок — where project:<Название>, text начинается с "Цель: " или "Дедлайн: "; в decisions их
не пиши: у каждого проекта есть поле цели, и оно должно заполняться, а не пустовать.
Теги money/health/private ставь, только если это личное о владельце (его деньги, его здоровье, его семья), а не
аудитория, рынок, бюджет проекта или чужие люди.
Источник calendar — встречи: бери людей, с кем он регулярно встречается, и проекты, а не каждую встречу.
Источник browser_history — заголовки прочитанных страниц: только устойчивые интересы, если тема повторяется
много раз, confidence не выше 0.6; о здоровье и личном по истории браузера выводов не делай.
Источник documents — его документы: бери проекты, роли, договорённости, а не содержимое документа.
Источник telegram_api — переписка в чате: реплики владельца помечены «Я:», остальные — именем собеседника. Бери факты
о владельце и о людях вокруг него (person:<Имя>: кто он владельцу, о чём договорились, что важно в общении);
слова собеседника о себе — факт о собеседнике, а не о владельце; чужие мнения владельцу не приписывай.

Верни ТОЛЬКО JSON: {{"facts": [{{
  "text": "одна строка на языке владельца",
  "kind": "fact|rule|decision|project|person|preference",
  "where": "card:<Тема>|project:<Название>|person:<Имя>|rules|decisions|profile:<раздел>|inbox",
  "key": "о чём факт, 2-4 слова (для поиска противоречий)",
  "tags": ["money"|"health"|"private"],
  "confidence": 0.0-1.0,
  "evidence": "короткая цитата владельца",
  "contradicts": "строка из известного, если противоречит, иначе пусто",
  "ref": "ref эпизода"
}}]}}
Пустой результат — {{"facts": []}}.

ИЗВЕСТНО СЕЙЧАС:
{known}

РЕПЛИКИ (JSON):
{episodes}
"""


def sensitive_tags(text: str) -> list[str]:
    return [t for t, rx in SENSITIVE.items() if re.search(rx, text, re.I)]


def _norm_where(c: dict) -> str:
    w = str(c.get("where") or "").strip()
    kind = c.get("kind")
    if kind == "rule":
        return "rules"
    if kind == "decision":
        return "decisions"
    if re.match(r"^(inbox|rules|decisions)$|^(project|person|profile|card):.+", w):
        return w
    return "inbox"


def clean(raw: list, episodes: list[Episode], source_by_ref: dict | None = None) -> list[dict]:
    """Validate brain output: drop junk, fix fields, add sensitive tags as a safety net."""
    refs = {e.ref: e for e in episodes}
    out = []
    for c in raw if isinstance(raw, list) else []:
        if not isinstance(c, dict):
            continue
        text = " ".join(str(c.get("text") or "").split())
        if len(text) < 6 or len(text) > 400:
            continue
        kind = c.get("kind") if c.get("kind") in KINDS else "fact"
        tags = sorted({t for t in (c.get("tags") or []) if t in SENSITIVE} | set(sensitive_tags(text)))
        try:
            conf = max(0.0, min(1.0, float(c.get("confidence", 0.5))))
        except (TypeError, ValueError):
            conf = 0.5
        ref = str(c.get("ref") or "")
        ep = refs.get(ref) or (episodes[0] if len(episodes) == 1 else None)
        correction = bool(ep and ep.prev and kind == "rule")
        where = _norm_where({**c, "kind": kind})
        if kind == "rule" and not correction and not RULE_MARK.search(text):
            # A one-off instruction for the current task ("сначала собери вопросы, потом план") is not a rule for
            # every future conversation. Keep it as a decision that waits for a repeat instead of a standing rule.
            kind, where, conf = "decision", "decisions", min(conf, 0.7)
        out.append(
            {
                "text": text,
                "kind": kind,
                "where": where,
                "key": " ".join(str(c.get("key") or "").split())[:60],
                "tags": tags,
                "confidence": conf,
                "evidence": " ".join(str(c.get("evidence") or "").split())[:300],
                "contradicts": " ".join(str(c.get("contradicts") or "").split())[:300],
                "ref": ep.ref if ep else ref,
                "source": ep.source if ep else "",
                "said_at": ep.ts if ep else "",
                "correction": correction,
            }
        )
    return out


def parse_json(text: str) -> list:
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return []
    try:
        d = json.loads(m.group(0))
    except ValueError:
        return []
    return d.get("facts", []) if isinstance(d, dict) else []


def batches(episodes: list[Episode], limit_chars: int = 12000) -> list[list[Episode]]:
    out, cur, size = [], [], 0
    for e in episodes:
        n = len(e.text) + len(e.prev) + 80
        if cur and size + n > limit_chars:
            out.append(cur)
            cur, size = [], 0
        cur.append(e)
        size += n
    if cur:
        out.append(cur)
    return out


def payload(episodes: list[Episode]) -> str:
    return json.dumps(
        [{"ref": e.ref, "source": e.source, "title": e.title, "ai_before": e.prev, "owner": e.text} for e in episodes],
        ensure_ascii=False,
    )


# ---------------------------------------------------------------- no model

EXPLICIT = re.compile(
    r"(?:^|[.!?\n]\s*)(?:запомни|запиши в память|сохрани в память|remember)\s*[,:]?\s*(?:что|that)?\s*(.{6,300}?)(?:$|[.!?\n])",
    re.I,
)
DECISION = re.compile(
    r"(?:^|[.!?\n]\s*)((?:я\s+)?(?:решил[аи]?|решено|договорились|выбираю|выбрал[аи]?|берём|берем)\b.{6,250}?)(?:$|[.!?\n])",
    re.I,
)
CORRECTION = re.compile(
    r"\b(нет,? не так|не то|не надо|я же (?:говорил|писал|просил|сказал)|сколько раз|опять ты|перестань|"
    r"зачем ты|не делай|прекрати|ты снова|that's wrong|i told you|stop doing)\b",
    re.I,
)
RULE_SENT = re.compile(
    r"(?:^|[.!?\n]\s*)([^.!?\n]*\b(?:никогда|всегда|не\s+\w+й|не\s+надо|только|без\s+\w+|always|never|don't)\b[^.!?\n]{3,200})",
    re.I,
)
STATUS = re.compile(r"([^.\n]{6,250}\((?:статус|status)\s+\d{1,2}\.\d{1,2}\.\d{4}\))", re.I)


class NoModelBrain:
    name = "none"

    def extract(self, episodes: list[Episode], known: str) -> list[dict]:
        raw = []
        for e in episodes:
            t = e.text
            for m in EXPLICIT.finditer(t):
                raw.append(
                    {
                        "text": m.group(1).strip(" ,:"),
                        "kind": "fact",
                        "where": "inbox",
                        "confidence": 0.95,
                        "evidence": m.group(0).strip()[:200],
                        "ref": e.ref,
                        "key": "",
                    }
                )
            for m in DECISION.finditer(t):
                raw.append(
                    {
                        "text": m.group(1).strip(),
                        "kind": "decision",
                        "confidence": 0.7,
                        "evidence": m.group(1).strip()[:200],
                        "ref": e.ref,
                    }
                )
            for m in STATUS.finditer(t):
                raw.append(
                    {
                        "text": m.group(1).strip(),
                        "kind": "fact",
                        "where": "inbox",
                        "confidence": 0.75,
                        "evidence": m.group(1).strip()[:200],
                        "ref": e.ref,
                        "key": re.sub(r"\(.*", "", m.group(1)).strip()[:40],
                    }
                )
            if e.prev and CORRECTION.search(t):
                rules = [m.group(1).strip() for m in RULE_SENT.finditer(t)]
                text = rules[0] if rules else t.split("\n")[0][:200]
                raw.append(
                    {
                        "text": text[0].upper() + text[1:],
                        "kind": "rule",
                        "confidence": 0.7 if rules else 0.5,
                        "evidence": t[:200],
                        "ref": e.ref,
                        "key": "",
                    }
                )
        return clean(raw, episodes)


# ---------------------------------------------------------------- model brains


class _LLMBrain:
    name = "llm"
    timeout = 300

    def ask(self, prompt: str) -> str:  # pragma: no cover - overridden
        raise NotImplementedError

    cloud = False  # the text leaves the computer: secrets are hidden first
    vault = None  # set by the learning loop: for the log of what went out

    def _ask_safe(self, prompt: str, purpose: str = "обучение") -> str:
        if not self.cloud:
            return self.ask(prompt)
        from .. import outgoing as OG

        on = True
        if self.vault is not None:
            from ..agent import profile as P

            on = P.load(self.vault).get("redact", True)
        red = OG.Redactor() if on else None
        sent = red.apply(prompt) + ("\n\n" + OG.NOTE if red.values else "") if red else prompt
        if self.vault is not None:
            OG.log(
                self.vault,
                self.name,
                getattr(self, "model", ""),
                len(sent),
                red.summary() if red else {},
                {"purpose": purpose},
            )
        raw = self.ask(sent)
        return red.restore(raw) if red else raw

    def extract(self, episodes: list[Episode], known: str) -> list[dict]:
        out = []
        for b in batches(episodes):
            prompt = PROMPT.format(mark=BRAIN_MARK, known=known[:6000] or "(пусто)", episodes=payload(b))
            out += clean(parse_json(self._ask_safe(prompt)), b)
        # explicit "запомни" must never be lost, even if the model skipped it
        explicit = [c for c in NoModelBrain().extract(episodes, known) if c["confidence"] >= 0.9]
        covered = {c["ref"] for c in out}  # the model already took something from that message
        return out + [c for c in explicit if c["ref"] not in covered]


def _npm_exe(folder: Path) -> Path | None:
    """The real program behind npm's claude.cmd shim (the shim mangles empty arguments on Windows)."""
    base = folder / "node_modules" / "@anthropic-ai"
    for cand in (
        base / "claude-code" / "bin" / "claude.exe",
        base / "claude-code" / "node_modules" / "@anthropic-ai" / "claude-code-win32-x64" / "claude.exe",
        base / "claude-code" / "node_modules" / "@anthropic-ai" / "claude-code-win32-arm64" / "claude.exe",
    ):
        if cand.is_file():
            return cand
    return None


def _newest(folder: Path, name: str) -> Path | None:
    """Claude Desktop keeps its own Claude Code in claude-code/<version>/: the newest one."""
    try:
        found = [d / name for d in folder.iterdir() if (d / name).is_file()]
    except OSError:
        return None

    def ver(p: Path):
        return tuple(int(x) for x in re.findall(r"\d+", p.parent.name)[:4])

    return max(found, key=ver) if found else None


def claude_places() -> list[Path]:
    """Where Claude Code lives besides PATH: a program started from a shortcut often has a shorter PATH than a terminal,
    and Claude Desktop brings its own copy that is never on PATH at all."""
    home = Path.home()
    env = os.environ.get
    if sys.platform == "win32":
        appdata = Path(env("APPDATA") or home / "AppData" / "Roaming")
        local = Path(env("LOCALAPPDATA") or home / "AppData" / "Local")
        out = [
            home / ".local" / "bin" / "claude.exe",  # the official installer
            local / "Microsoft" / "WinGet" / "Links" / "claude.exe",
            local / "Volta" / "bin" / "claude.exe",
            home / ".bun" / "bin" / "claude.exe",
            home / "scoop" / "shims" / "claude.exe",
            local / "Programs" / "claude" / "claude.exe",
        ]
        npm_dirs = [appdata / "npm"] + sorted((appdata / "nvm").glob("v*"), reverse=True)
        for d in npm_dirs:
            exe = _npm_exe(d)
            if exe:
                out.append(exe)
        for pkg in sorted((local / "Microsoft" / "WinGet" / "Packages").glob("Anthropic.ClaudeCode*")):
            out += list(pkg.glob("**/claude.exe"))[:1]
        desk = _newest(appdata / "Claude" / "claude-code", "claude.exe")
        if desk:
            out.append(desk)
        return out
    out = [
        home / ".local" / "bin" / "claude",
        home / ".claude" / "local" / "claude",
        home / ".npm-global" / "bin" / "claude",
        home / ".bun" / "bin" / "claude",
        home / ".volta" / "bin" / "claude",
        Path("/opt/homebrew/bin/claude"),
        Path("/usr/local/bin/claude"),
        Path("/usr/bin/claude"),
    ]
    out += sorted(home.glob(".nvm/versions/node/*/bin/claude"), reverse=True)
    desk_dir = (
        home / "Library" / "Application Support" / "Claude" / "claude-code"
        if sys.platform == "darwin"
        else home / ".config" / "Claude" / "claude-code"
    )
    desk = _newest(desk_dir, "claude")
    if desk:
        out.append(desk)
    return out


def claude_exe() -> str | None:
    """The real Claude Code program: on PATH first, then where installers and Claude Desktop put it."""
    exe = shutil.which("claude.exe") if sys.platform == "win32" else None
    if exe:
        return exe
    shim = shutil.which("claude")
    if shim and sys.platform == "win32":
        real = _npm_exe(Path(shim).parent)
        if real:
            return str(real)
    if shim and not shim.lower().endswith((".cmd", ".bat", ".ps1")):
        return shim
    for p in claude_places():
        if p.is_file():
            return str(p)
    return shim


def claude_signed_in() -> bool:
    """Claude Code is installed AND someone is signed in to it (a subscription or a Console key). Installed alone is not
    enough: «Claude по подписке» must never be shown as connected to a person who has no Claude account."""
    if not claude_exe():
        return False
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        return True
    cfg = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    if (cfg / ".credentials.json").is_file():
        return True
    try:  # the signed-in account Claude Code keeps in ~/.claude.json
        if (json.loads((Path.home() / ".claude.json").read_text(encoding="utf-8")) or {}).get("oauthAccount"):
            return True
    except (OSError, ValueError):
        pass
    if sys.platform == "darwin":  # macOS keeps the sign-in in the Keychain
        try:
            r = subprocess.run(
                ["security", "find-generic-password", "-s", "Claude Code-credentials"], capture_output=True, timeout=10
            )
            return r.returncode == 0
        except Exception:
            return False
    return False


def claude_settings_env() -> dict:
    """ANTHROPIC_* from Claude Code's own settings.json. Mnemai runs the CLI with --setting-sources "" (no hooks, no
    MCP, no project files) — right for privacy, but it also hides a proxy or a subscription configured there, and then
    «Claude по подписке» answers «Not logged in» although the owner is signed in. Environment variables are inherited
    by the child process anyway, so pass exactly the ANTHROPIC_* ones through."""
    import json as _json

    p = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / "settings.json"
    try:
        env = _json.loads(p.read_text(encoding="utf-8")).get("env") or {}
    except (OSError, ValueError, TypeError):
        return {}
    if not isinstance(env, dict):
        return {}
    return {
        k: str(v)
        for k, v in env.items()
        if str(k).startswith("ANTHROPIC_") and isinstance(v, str) and k not in os.environ
    }


class ClaudeCodeBrain(_LLMBrain):
    """Headless Claude Code: no tools, no hooks/settings, no MCP, session not saved.
    Runs in its own folder so its transcripts (if any) are never read back as the owner's words."""

    name = "claude_code"
    cloud = True

    def __init__(self, cwd: Path, model: str = ""):
        self.cwd, self.model = cwd, model

    def ask(self, prompt: str) -> str:
        exe = claude_exe()
        if not exe:
            raise RuntimeError("Claude Code не найден. Установи его или выбери другой мозг")
        self.cwd.mkdir(parents=True, exist_ok=True)
        # outside any git repo: otherwise Claude Code puts the repo's git status (file names) into the prompt
        from .. import net

        # Claude Code keeps no notes of its own about what it read here (its auto-memory)
        env = net.env(
            {
                **claude_settings_env(),
                "GIT_CEILING_DIRECTORIES": str(self.cwd.parent),
                "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
            }
        )
        args = [
            exe,
            "-p",
            "--output-format",
            "json",
            "--no-session-persistence",
            "--tools",
            "",
            "--setting-sources",
            "",
            "--strict-mcp-config",
        ] + (["--model", self.model] if self.model else [])
        r = subprocess.run(
            args,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=self.cwd,
            timeout=self.timeout,
            env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if r.returncode != 0:
            raise RuntimeError(f"Claude Code: {(r.stderr or r.stdout)[:300]}")
        try:
            return json.loads(r.stdout).get("result", "")
        except ValueError:
            return r.stdout


def _post(url: str, body: dict, headers: dict, timeout: int) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", **headers},
    )
    with net.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


class ApiBrain(_LLMBrain):
    name = "api"
    cloud = True

    def __init__(self, provider: str, api_key: str, model: str, endpoint: str = ""):
        if not api_key or not model:
            raise RuntimeError("Для своего ключа нужны ключ и название модели")
        self.provider, self.key, self.model, self.endpoint = provider, api_key, model, endpoint.rstrip("/")

    def ask(self, prompt: str) -> str:
        if self.provider == "anthropic":
            d = _post(
                (self.endpoint or "https://api.anthropic.com") + "/v1/messages",
                {"model": self.model, "max_tokens": 4000, "messages": [{"role": "user", "content": prompt}]},
                {"x-api-key": self.key, "anthropic-version": "2023-06-01"},
                self.timeout,
            )
            return "".join(b.get("text", "") for b in d.get("content", []))
        d = _post(
            (self.endpoint or "https://api.openai.com/v1") + "/chat/completions",
            {"model": self.model, "messages": [{"role": "user", "content": prompt}]},
            {"Authorization": f"Bearer {self.key}"},
            self.timeout,
        )
        return d["choices"][0]["message"]["content"]


class LocalBrain(_LLMBrain):
    """The model built into Mnemai (llama.cpp on this computer)."""

    name = "local"

    def __init__(self, model: str = ""):
        self.model = model

    def ask(self, prompt: str) -> str:
        from ..localllm import ensure_server

        port = ensure_server(self.model)
        d = _post(
            f"http://127.0.0.1:{port}/v1/chat/completions",
            {"model": "local", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2},
            {},
            self.timeout,
        )
        return d["choices"][0]["message"]["content"]


class OllamaBrain(_LLMBrain):
    name = "ollama"

    def __init__(self, model: str, endpoint: str = ""):
        if not model:
            raise RuntimeError("Укажи модель Ollama, например qwen2.5:14b")
        self.model, self.endpoint = model, (endpoint or "http://127.0.0.1:11434").rstrip("/")

    def ask(self, prompt: str) -> str:
        d = _post(
            self.endpoint + "/api/chat",
            {"model": self.model, "stream": False, "format": "json", "messages": [{"role": "user", "content": prompt}]},
            {},
            self.timeout,
        )
        return (d.get("message") or {}).get("content", "")


class ModelBrain(_LLMBrain):
    """The model the owner talks to by default, whatever it is: a cloud AI by key or subscription, or one on this
    computer. No model is preferred by name."""

    name = "model"

    def __init__(self):
        self.vault = None  # set by the learner before the first question

    @property
    def cloud(self) -> bool:
        return self._ref().partition(":")[0] not in ("local", "ollama", "strata")

    def _ref(self) -> str:
        from ..chat import engine as CH

        ref = CH.default_model(self.vault) if self.vault else ""
        if not ref:
            raise RuntimeError("не подключено ни одной модели")
        return ref

    def ask(self, prompt: str) -> str:
        from ..chat import providers as PR

        pid, _, model = self._ref().partition(":")
        return PR.complete(self.vault, pid, model, "", [{"role": "user", "text": prompt}], meta={"purpose": "обучение"})

    def extract(self, episodes, known):
        try:
            return super().extract(episodes, known)
        except Exception:  # no model or no network: «запомни» and corrections still work
            return NoModelBrain().extract(episodes, known)


def brain_dir() -> Path:
    """Where headless Claude Code runs: an empty folder in TEMP, outside the memory and any repository."""
    return Path(tempfile.gettempdir()) / "mnema-brain"


def make_brain(settings: dict, brain_cwd: Path | None = None):
    brain_cwd = brain_cwd or brain_dir()
    from .settings import resolve_brain

    b = settings["brain"]
    kind = resolve_brain(settings)
    if kind == "model":
        return ModelBrain()
    if kind == "claude_code":
        return ClaudeCodeBrain(brain_cwd, b.get("model", ""))
    if kind == "api":
        return ApiBrain(b.get("provider", "anthropic"), b.get("api_key", ""), b.get("model", ""), b.get("endpoint", ""))
    if kind == "ollama":
        return OllamaBrain(b.get("model", ""), b.get("endpoint", ""))
    if kind == "local":
        return LocalBrain(b.get("model", ""))
    return NoModelBrain()
