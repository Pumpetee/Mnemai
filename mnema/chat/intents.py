"""Short commands the owner says to the computer, answered without asking a model.

«Открой терминал», «запусти firefox», «open https://…» are one action, not a conversation: doing them through a
40–90 s model call (and two calls: the action, then the retelling) is why a simple request felt like a hang. Here
the recognised command goes straight to the same open_app action the chat uses, for every model.
"""

from __future__ import annotations

import re
import shutil

from ..vault import Vault
from . import tools as TL

OPEN = re.compile(
    r"^\s*(?:пожалуйста[,\s]+)?(?:открой(?:те)?|запусти(?:те)?|открывай(?:те)?|open|launch)\s+(?:мне\s+)?(.+?)\s*[.!?]*$",
    re.I,
)
POLITE = re.compile(r"[,\s]*(?:пожалуйста|плиз|please)[.!?]*$", re.I)
# Names the owner may say besides the executable names the action already knows.
NAMES = {
    "терминал": "terminal",
    "терминала": "terminal",
    "консоль": "terminal",
    "консолька": "terminal",
    "terminal": "terminal",
    "console": "terminal",
    "konsole": "terminal",
    "хром": "chrome",
    "chrome": "chrome",
    "гугл хром": "chrome",
    "google chrome": "chrome",
    "браузер chrome": "chrome",
    "файрфокс": "firefox",
    "firefox": "firefox",
    "мозила": "firefox",
    "телеграм": "telegram",
    "телеграмм": "telegram",
    "telegram": "telegram",
    "код": "code",
    "vscode": "code",
    "vs code": "code",
    "файловый менеджер": "dolphin",
    "проводник": "dolphin",
    "dolphin": "dolphin",
}


def fast_open(vault: Vault, text: str) -> dict | None:
    """The action to do right now, or None if this is ordinary talk (then the model answers)."""
    if not TL.pc_enabled(vault):
        return None
    m = OPEN.match((text or "").strip())
    if not m:
        return None
    target = POLITE.sub("", m.group(1)).strip().strip(" «»\"'").strip()
    if not target or len(target) > 200 or "\n" in target:
        return None
    low = target.lower()
    if low.startswith(("http://", "https://")):
        return {"tool": "open_app", "name": target, "label": "ссылка"}
    if low.startswith("www."):
        return {"tool": "open_app", "name": "https://" + target, "label": "ссылка"}
    if low in NAMES:
        return {"tool": "open_app", "name": NAMES[low], "label": NAMES[low]}
    if low in TL.APP_ALIASES:
        return {"tool": "open_app", "name": low, "label": low}
    if shutil.which(target) or shutil.which(low):  # an installed program by its own name
        return {"tool": "open_app", "name": low, "label": low}
    return None


def answer(vault: Vault, call: dict) -> str:
    """Do the action and say one short line — the way the owner asked."""
    line = ""
    try:
        _, line, _ = TL.run(vault, {"tool": "open_app", "name": call["name"]}, "owner")
    except TL.Refused as e:
        return str(e)[:300]
    label = call.get("label") or call.get("name") or ""
    if label == "ссылка":
        return "Готово — открыла ссылку."
    nice = line.replace("Открыла: ", "")
    if nice:
        return f"Готово — открыла {nice}."
    return "Готово."
