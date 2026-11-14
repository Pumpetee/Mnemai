"""The rest of digital life: calendar, documents, browser history.

calendar          — an .ics file or a secret iCal link (Google Calendar → settings → "secret address in iCal format").
                    Meetings of the past days and the next two weeks: who, what, when.
documents         — a folder of .txt, .md and .docx: only new or changed files, text only.
browser_history   — Chrome, Edge or Yandex Browser history: titles of pages read, grouped by day. Reads a copy,
                    never the live file. Defaults to "observe" — it's the most personal source.
"""

from __future__ import annotations

import datetime as dt
import os
import re
import sys
import shutil
import sqlite3
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from ..vault import Vault
from .sources import Episode, _clip, _since


# ---------------------------------------------------------------- calendar (.ics)


def _ics_unfold(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        if line[:1] in (" ", "\t") and out:
            out[-1] += line[1:]
        else:
            out.append(line)
    return out


def _ics_date(v: str) -> dt.datetime | None:
    v = v.strip()
    utc = v.endswith("Z")
    v = v.rstrip("Z")
    for fmt in ("%Y%m%dT%H%M%S", "%Y%m%d"):
        try:
            d = dt.datetime.strptime(v[:15] if "T" in v else v[:8], fmt)
            if utc:
                d = d.replace(tzinfo=dt.timezone.utc).astimezone().replace(tzinfo=None)
            return d
        except ValueError:
            continue
    return None


def parse_ics(text: str) -> list[dict]:
    events, cur = [], None
    for line in _ics_unfold(text):
        if line == "BEGIN:VEVENT":
            cur = {}
        elif line == "END:VEVENT" and cur is not None:
            events.append(cur)
            cur = None
        elif cur is not None and ":" in line:
            k, v = line.split(":", 1)
            key = k.split(";")[0].upper()
            v = v.replace("\\n", " ").replace("\\,", ",").replace("\\;", ";").strip()
            if key in ("SUMMARY", "DESCRIPTION", "LOCATION", "UID"):
                cur[key.lower()] = v
            elif key in ("DTSTART", "DTEND"):
                cur[key.lower()] = _ics_date(v)
            elif key == "ATTENDEE":
                cur.setdefault("attendees", []).append(re.sub(r"^mailto:", "", v, flags=re.I))
    return events


def read_calendar(vault: Vault, opts: dict, cursor: dict, days: int | None, limit: int, fetch=None) -> list[Episode]:
    src = str(opts.get("path") or "").strip()
    if not src:
        return []
    if src.startswith(("http://", "https://", "webcal://")):
        url = "https://" + src[len("webcal://") :] if src.startswith("webcal://") else src
        text = (fetch or (lambda u: urllib.request.urlopen(u, timeout=30).read().decode("utf-8", "replace")))(url)
    else:
        p = Path(src).expanduser()
        if not p.exists():
            return []
        text = p.read_text(encoding="utf-8", errors="replace")
    now = dt.datetime.now()
    lo = now - dt.timedelta(days=min(days or 14, 30))
    hi = now + dt.timedelta(days=14)
    seen = set(cursor.get("uids", []))
    out = []
    for ev in sorted(parse_ics(text), key=lambda e: e.get("dtstart") or now):
        start = ev.get("dtstart")
        if not start or not (lo <= start <= hi):
            continue
        uid = (ev.get("uid") or "") + start.isoformat()
        if uid in seen:
            continue
        seen.add(uid)
        when = "прошло" if start < now else "предстоит"
        parts = [f"Встреча ({when}) {start:%d.%m.%Y %H:%M}: {ev.get('summary', 'без названия')}"]
        if ev.get("attendees"):
            parts.append("Участники: " + ", ".join(ev["attendees"][:8]))
        if ev.get("location"):
            parts.append("Где: " + ev["location"])
        if ev.get("description"):
            parts.append(_clip(ev["description"], 500))
        out.append(Episode("calendar", uid[:80], start.isoformat(), "\n".join(parts), title=ev.get("summary", "")))
        if len(out) >= limit:
            break
    cursor["uids"] = sorted(seen)[-2000:]
    return out


# ---------------------------------------------------------------- documents


def docx_text(path: Path) -> str:
    """Paragraphs line by line, a table row by row with « | » between the cells, tabs and breaks kept."""
    import xml.etree.ElementTree as ET

    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(path) as z:
        raw = z.read("word/document.xml")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        import html

        xml = re.sub(r"</w:p>", "\n", raw.decode("utf-8", "replace"))
        return html.unescape(re.sub(r"<[^>]+>", "", xml))

    def para(p) -> str:
        out = []
        for el in p.iter():
            if el.tag == W + "t":
                out.append(el.text or "")
            elif el.tag == W + "tab":
                out.append("\t")
            elif el.tag in (W + "br", W + "cr"):
                out.append("\n")
        return "".join(out)

    lines: list[str] = []

    def walk(node):
        for ch in node:
            if ch.tag == W + "p":
                lines.append(para(ch))
            elif ch.tag == W + "tbl":
                for tr in ch.iter(W + "tr"):
                    cells = [" ".join(para(p) for p in tc.iter(W + "p")).strip() for tc in tr.findall(W + "tc")]
                    lines.append(" | ".join(cells))
            else:
                walk(ch)

    body = root.find(W + "body")
    walk(body if body is not None else root)
    return "\n".join(lines) + "\n"


def read_documents(vault: Vault, opts: dict, cursor: dict, days: int | None, limit: int) -> list[Episode]:
    root = Path(str(opts.get("path") or "")).expanduser()
    if not str(opts.get("path") or "") or not root.exists():
        return []
    vroot = vault.root.resolve()
    since = _since(days)
    known = cursor.setdefault("files", {})
    out = []
    files = [f for ext in ("*.txt", "*.md", "*.docx") for f in root.rglob(ext)]
    for f in sorted(files, key=lambda f: f.stat().st_mtime):
        rp = f.resolve()
        if vroot == rp or vroot in rp.parents or f.name.startswith(("~$", ".")):
            continue
        st = f.stat()
        key = str(f.relative_to(root))
        if st.st_mtime < since or known.get(key, 0) >= st.st_mtime:
            continue
        try:
            text = docx_text(f) if f.suffix.lower() == ".docx" else f.read_text(encoding="utf-8", errors="replace")
        except (zipfile.BadZipFile, KeyError, OSError):
            continue
        known[key] = st.st_mtime
        if len(text.strip()) < 40:
            continue
        out.append(
            Episode(
                "documents",
                key,
                dt.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
                _clip(text, 4000),
                title=f.stem,
            )
        )
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------- browser history


def history_files() -> dict[str, Path]:
    if sys.platform == "win32":
        local = Path(os.environ.get("LOCALAPPDATA", ""))
        cands = {
            "Chrome": local / "Google/Chrome/User Data/Default/History",
            "Edge": local / "Microsoft/Edge/User Data/Default/History",
            "Яндекс Браузер": local / "Yandex/YandexBrowser/User Data/Default/History",
        }
    elif sys.platform == "darwin":
        sup = Path.home() / "Library" / "Application Support"
        cands = {
            "Chrome": sup / "Google/Chrome/Default/History",
            "Edge": sup / "Microsoft Edge/Default/History",
            "Яндекс Браузер": sup / "Yandex/YandexBrowser/Default/History",
        }
    else:
        cfg = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
        cands = {
            "Chrome": cfg / "google-chrome/Default/History",
            "Chromium": cfg / "chromium/Default/History",
            "Edge": cfg / "microsoft-edge/Default/History",
            "Яндекс Браузер": cfg / "yandex-browser/Default/History",
        }
    return {k: v for k, v in cands.items() if v.exists()}


SKIP_TITLES = re.compile(r"^(new tab|новая вкладка|google|яндекс|youtube|вход|login|sign in)$", re.I)


def read_browser_history(
    vault: Vault, opts: dict, cursor: dict, days: int | None, limit: int, files: dict | None = None
) -> list[Episode]:
    """Titles of pages, grouped per day. Works on a temporary copy — the browser keeps its file locked."""
    files = files if files is not None else history_files()
    want = opts.get("browser") or ""
    out = []
    for name, path in files.items():
        if want and want != name:
            continue
        tmp = Path(tempfile.mkdtemp()) / "History"
        try:
            shutil.copy2(path, tmp)
            con = sqlite3.connect(f"file:{tmp}?mode=ro", uri=True)
            # Chrome time: microseconds since 1601-01-01
            last = int(cursor.get(name, 0))
            floor = int(
                (dt.datetime.now() - dt.timedelta(days=min(days or 7, 30)) - dt.datetime(1601, 1, 1)).total_seconds()
                * 1e6
            )
            rows = con.execute(
                "SELECT v.visit_time, u.title, u.url FROM visits v JOIN urls u ON u.id = v.url "
                "WHERE v.visit_time > ? ORDER BY v.visit_time",
                (max(last, floor),),
            ).fetchall()
            con.close()
        except (OSError, sqlite3.Error):
            continue
        finally:
            shutil.rmtree(tmp.parent, ignore_errors=True)
        by_day: dict[str, list[str]] = {}
        for t, title, url in rows:
            title = (title or "").strip()
            if not title or SKIP_TITLES.match(title):
                continue
            day = (
                (dt.datetime(1601, 1, 1, tzinfo=dt.timezone.utc) + dt.timedelta(microseconds=t))
                .astimezone()
                .strftime("%Y-%m-%d")
            )  # local day: a 23:30 UTC visit must not land on the previous day
            lst = by_day.setdefault(day, [])
            if title not in lst:
                lst.append(title)
            cursor[name] = max(int(cursor.get(name, 0)), t)
        for day, titles in sorted(by_day.items()):
            out.append(
                Episode(
                    "browser_history",
                    f"{name}@{day}",
                    day,
                    _clip("Читал(а) в браузере:\n" + "\n".join(f"- {x}" for x in titles[:80]), 4000),
                    title=f"{name}, {day}",
                )
            )
            if len(out) >= limit:
                return out
    return out
