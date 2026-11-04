"""Which models of a provider go on top: the current good ones first, old and special-purpose ones last.

Providers list everything they have, alphabetically or by date: «chatgpt-image-latest», «gpt-3.5-turbo-0125» and
text-to-speech models sit next to the ones people want. The menu shows the top few of each provider; the rest stay
behind «Все модели», with the old ones at the very end. Nothing here names a «best» model by hand: the order comes
from how new a model is (the provider's own date where it gives one) and how big it is (mini, flash, nano are lighter).
"""

from __future__ import annotations

import re

# not a chat model at all, an outdated generation, a dated snapshot of a model that also has a plain name, or a model
# the chat endpoint does not serve (Responses-only, research agents)
_OLD = re.compile(
    r"embed|tts|whisper|transcri|audio|realtime|speech|image|dall-e|imagen|veo|moderation|search|computer-use|"
    r"davinci|babbage|instruct|codex|deep-research|robotics|aqa|learnlm|"
    r"(^|/)gpt-3\.5|(^|/)gpt-4(?![.o])|(^|/)o1(-mini|-preview)?$|(^|/)chatgpt-4o|"
    r"(^|[-/])claude-(instant|2|3)(?!\.7|-7)|"
    r"-\d{4}-\d{2}-\d{2}$|-\d{4}$|-\d{3}$|-exp(-\d+)?$|-preview-\d{2}-\d{2}$|(^|/)gemma|(^|/)(gpt-\d[\w.]*|o\d)-pro$",
    re.I,
)
_LIGHT = re.compile(r"(?<![a-z])mini|flash|haiku|small|fast", re.I)  # not the «mini» inside «gemini»
_LIGHTER = re.compile(r"nano|lite|tiny", re.I)
# OpenRouter offers hundreds of models from everyone: the well-known makers go first
_KNOWN = ("anthropic/", "openai/", "google/", "deepseek/", "x-ai/", "mistralai/", "qwen/", "meta-llama/", "moonshotai/")


def old(mid: str) -> bool:
    return bool(_OLD.search(mid or ""))


def _version(mid: str) -> float:
    """A rough «how new» from the name when the provider gives no date: gpt-5.1 > gpt-4o, gemini-2.5 > gemini-2.0,
    claude-opus-4-1-20250805 → its date."""
    d = re.search(r"(20\d{2})(\d{2})(\d{2})", mid)
    if d:
        return float(d.group(0))
    m = re.search(r"(\d+)(?:[.-](\d))?(?!\d)", mid.split("/")[-1])
    return float(f"{m.group(1)}.{m.group(2) or 0}") if m else 0.0


def rank(pid: str, ids: list[str], created: dict | None = None) -> list[str]:
    """ids ordered: good ones by tier (full, light, lighter) and newness, then the old ones."""
    created = created or {}
    if pid in ("local", "ollama", "strata", "claude_code", "codex", "opencode_go", "yandex"):
        return list(ids)  # what the owner installed, or a fixed short list: kept as it is

    def key(mid: str):
        tier = 2 if _LIGHTER.search(mid) else 1 if _LIGHT.search(mid) else 0
        when = float(created.get(mid) or 0) or _version(mid)
        known = 0 if pid != "openrouter" or mid.startswith(_KNOWN) else 1
        return (old(mid), known, tier, -when, mid)

    return sorted(dict.fromkeys(i for i in ids if i), key=key)
