"""Attached files: saved next to the chat, turned into something each model can read.

text-like and .docx — the text goes into the message for every model;
images and PDF — Claude by subscription reads them with its Read tool (only this chat's folder is open to it),
Anthropic gets them as image/document blocks, OpenAI-compatible and Ollama get images; PDF there is refused honestly.
"""

from __future__ import annotations

import base64
import re
from pathlib import Path

from ..vault import Vault

TEXT_EXT = {
    ".txt",
    ".md",
    ".csv",
    ".tsv",
    ".json",
    ".xml",
    ".html",
    ".htm",
    ".yaml",
    ".yml",
    ".log",
    ".ini",
    ".py",
    ".js",
    ".ts",
    ".css",
    ".sql",
    ".sh",
    ".bat",
    ".ps1",
    ".java",
    ".c",
    ".cpp",
    ".cs",
    ".go",
    ".rs",
    ".rtf",
}
IMAGE_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
MAX_BYTES = 100 * 1024 * 1024  # the owner's limit: one attachment is at most 100 MB
MAX_TEXT = 60000


def safe_name(name: str) -> str:
    n = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "_", Path(name or "file").name).strip(" .") or "file"
    return n[:120]


def save(vault: Vault, chat_id: str, files: list[dict]) -> list[dict]:
    """files: [{name, data: base64}] → [{name, path, kind, mime, size, text?}]"""
    from .engine import _dir

    folder = _dir(vault) / chat_id / "files"
    folder.mkdir(parents=True, exist_ok=True)
    out = []
    for f in files or []:
        raw = base64.b64decode(str(f.get("data", "")).split(",")[-1] or b"")
        if len(raw) > MAX_BYTES:
            raise ValueError(f"файл {f.get('name')} больше 100 МБ")
        name = safe_name(f.get("name", "file"))
        p = folder / name
        i = 1
        while p.exists():
            p = folder / f"{p.stem}_{i}{p.suffix}"
            i += 1
        p.write_bytes(raw)
        ext = p.suffix.lower()
        item = {"name": p.name, "path": str(p), "size": len(raw)}
        from .. import docs

        from ..agent import profile as P

        lang = P.load(vault).get("lang") or "en"
        text = None
        if ext in docs.SUPPORTED:
            try:
                text, info = docs.extract(p, lang)  # read on the computer, free (scans recognised too)
                item["info"] = info
            except docs.LockedPdf:
                p.unlink(missing_ok=True)
                raise ValueError(
                    f"PDF «{name}» защищён паролем: Mnemai не может его прочитать. Сними пароль (например, открой "
                    "и выбери «Печать → Сохранить как PDF») и прикрепи снова."
                ) from None
            except Exception as e:
                item["error"] = str(e)[:200]
        if text is None and ext not in docs.SUPPORTED and (ext in TEXT_EXT or _looks_text(raw)):
            text = raw.decode("utf-8", "replace")
        pages = (item.get("info") or {}).get("pages") or 1
        if ext == ".pdf" and (text is None or docs.scanned(text, pages)):  # a scan nothing could be read from
            item.update(kind="pdf", mime="application/pdf")  # goes to the model as a file
        elif text is not None:
            tp = p.with_name(p.name + ".txt")
            tp.write_text(text, encoding="utf-8")
            item.update(kind="text", text=text[:2000], text_path=str(tp), chars=len(text))
        elif ext in IMAGE_MIME:
            item.update(kind="image", mime=IMAGE_MIME[ext])
            from .. import ocr

            seen = ocr.image_text(p, lang)  # the text on it, for every model — not only those that see pictures
            if len(re.sub(r"\s", "", seen)) >= 8:
                tp = p.with_name(p.name + ".txt")
                tp.write_text(seen, encoding="utf-8")
                item.update(ocr_path=str(tp), chars=len(seen))
        else:
            item.update(kind="other")
        out.append(item)
    return out


def _looks_text(raw: bytes) -> bool:
    try:
        raw[:4000].decode("utf-8")
        return b"\x00" not in raw[:4000]
    except UnicodeDecodeError:
        return False


def inline_text(text: str, files: list[dict]) -> str:
    """The message as the model sees it: text files pasted in."""
    parts = [text]
    for f in files or []:
        if f.get("kind") == "text":
            tp = Path(f["text_path"]) if f.get("text_path") else None
            full = tp.read_text(encoding="utf-8", errors="replace") if tp and tp.exists() else f.get("text", "")
            parts.append(f"\n\n[Прикреплённый файл «{f['name']}»]\n```\n{full[:MAX_TEXT]}\n```")
        elif f.get("kind") == "image" and f.get("ocr_path") and Path(f["ocr_path"]).exists():
            seen = Path(f["ocr_path"]).read_text(encoding="utf-8", errors="replace")
            parts.append(f"\n\n[Текст на картинке «{f['name']}», распознан на компьютере]\n```\n{seen[:MAX_TEXT]}\n```")
        elif f.get("kind") == "other":
            parts.append(f"\n\n[Прикреплён файл «{f['name']}» — формат не читается, только имя]")
    return "".join(parts)


def b64(path: str) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode()
