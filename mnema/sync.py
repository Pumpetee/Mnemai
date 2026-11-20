"""Free sync of the memory between computers, as open files (the owner's choice).

Targets:
- gdrive  — the folder of Google Drive for desktop («Мой диск» / «My Drive»), subfolder Mnemai;
- dropbox — the Dropbox folder (from Dropbox's own info.json), subfolder Mnemai;
- folder  — any folder (a NAS, a USB disk, another cloud client);
- station — the owner's own Mnemai station on a server (mnema station): the same memory over HTTP, plus MCP for any agent.

What travels: the memory notes (*.md) except the generated «10 Now» and «Index» and the per-computer «95 Saves»;
conversations (.mnema/chats/*.json) and access rules (.mnema/clients.json). Never: keys (they live in Windows),
tokens, learning state, engine settings of this computer.

Three-way merge with the state of the last sync: changed on one side → copied to the other; deleted on one side →
deleted on the other (a copy goes to «95 Saves» first); changed on both → this computer's version stays, the other one
lands next to it as «<name> (с другого устройства <дата>).md» and the owner is told.
"""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import os
import string
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

from .vault import GENERATED, SAVES, Vault

KINDS = ("gdrive", "dropbox", "folder", "station")
NAMES = {"gdrive": "Google Drive", "dropbox": "Dropbox", "folder": "Своя папка", "station": "MCP-станция"}
SUB = "Mnemai"
CHANGE_MIN = 600  # BP-13: изменения запускают синк не чаще раза в 10 минут
RETRY_MIN = 300  # BP-13: недоступная цель — повтор через 5 минут
_lock = threading.Lock()
_last: dict[str, dict] = {}


# ---------------------------------------------------------------- what is synced


def wanted(rel: str) -> bool:
    if rel in GENERATED or rel.startswith(SAVES + "/") or "/.." in "/" + rel:
        return False
    if rel.startswith(".mnema/"):
        return rel == ".mnema/clients.json" or (
            rel.startswith(".mnema/chats/") and rel.count("/") == 2 and rel.endswith(".json")
        )
    if any(p.startswith(".") for p in rel.split("/")):
        return False
    return rel.endswith(".md")


def _h(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:20]


def local_files(root: Path) -> dict[str, str]:
    out = {}
    if not root.exists():
        return out
    for p in root.rglob("*"):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            if wanted(rel):
                try:
                    out[rel] = _h(p.read_bytes())
                except PermissionError:  # encrypted with a key not open here: listed as it is, never taken as gone
                    try:
                        with open(p, "rb") as fh:
                            out[rel] = _h(fh.read())
                    except OSError:
                        pass
                except OSError:
                    pass
    return out


# ---------------------------------------------------------------- targets


class FolderTarget:
    def __init__(self, path: str):
        self.root = Path(path)

    def ready(self) -> tuple[bool, str]:
        if not self.root.parent.exists():
            return False, f"папки нет: {self.root.parent}"
        self.root.mkdir(parents=True, exist_ok=True)
        return True, ""

    def list(self) -> dict[str, str]:
        return local_files(self.root)

    def get(self, rel: str) -> bytes:
        return (self.root / rel).read_bytes()

    def put(self, rel: str, data: bytes) -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".mnema-tmp")
        tmp.write_bytes(data)
        os.replace(tmp, p)

    def delete(self, rel: str) -> None:
        (self.root / rel).unlink(missing_ok=True)


class StationTarget:
    def __init__(self, url: str, token: str):
        self.url, self.token = url.rstrip("/"), token

    def _req(self, method: str, path: str, rel: str = "", data: bytes | None = None):
        from . import net

        q = "?rel=" + urllib.parse.quote(rel) if rel else ""
        token = base64.urlsafe_b64encode(self.token.encode("utf-8")).decode("ascii")  # HTTP headers are latin-1
        req = urllib.request.Request(
            self.url + path + q,
            data=data,
            method=method,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/octet-stream"},
        )
        with net.urlopen(req, timeout=60) as r:
            return r.read()

    def ready(self) -> tuple[bool, str]:
        if not self.token:
            return False, "нет ключа станции"
        try:
            self._req("GET", "/sync/list")
            return True, ""
        except Exception as e:
            return False, f"станция не отвечает: {str(e)[:120]}"

    def list(self) -> dict[str, str]:
        return json.loads(self._req("GET", "/sync/list"))

    def get(self, rel: str) -> bytes:
        return self._req("GET", "/sync/file", rel)

    def put(self, rel: str, data: bytes) -> None:
        self._req("PUT", "/sync/file", rel, data)

    def delete(self, rel: str) -> None:
        self._req("DELETE", "/sync/file", rel)


# ---------------------------------------------------------------- where the clouds are on this computer


def find_gdrive() -> str:
    names = ("Мой диск", "My Drive")
    for letter in string.ascii_uppercase[3:]:  # Google Drive for desktop mounts a drive letter
        for n in names:
            p = Path(f"{letter}:/") / n
            try:
                if p.is_dir():
                    return str(p)
            except OSError:
                continue
    for n in ("Google Drive", "Google Диск"):
        p = Path.home() / n
        if p.is_dir():
            for sub in names:
                if (p / sub).is_dir():
                    return str(p / sub)
            return str(p)
    return ""


def find_dropbox() -> str:
    for base in (os.environ.get("LOCALAPPDATA"), os.environ.get("APPDATA")):
        if not base:
            continue
        f = Path(base) / "Dropbox" / "info.json"
        try:
            info = json.loads(f.read_text(encoding="utf-8"))
            for kind in ("personal", "business"):
                if info.get(kind, {}).get("path"):
                    return info[kind]["path"]
        except (OSError, ValueError):
            pass
    p = Path.home() / "Dropbox"
    return str(p) if p.is_dir() else ""


def detected() -> dict:
    return {"gdrive": find_gdrive(), "dropbox": find_dropbox()}


# ---------------------------------------------------------------- settings


def settings(vault: Vault) -> dict:
    from .agent import profile as P

    s = P.load(vault).get("sync") or {}
    return {"targets": s.get("targets") or [], "minutes": int(s.get("minutes") or 10)}


def target_of(vault: Vault, t: dict):
    kind = t.get("kind")
    if kind == "station":
        from .learn import secrets_store
        from .learn.settings import _vid

        return StationTarget(t.get("url", ""), secrets_store.get(_vid(vault), "sync.station." + t.get("id", "")))
    base = t.get("path") or (detected().get(kind) if kind in ("gdrive", "dropbox") else "")
    if not base:
        return None
    return FolderTarget(str(Path(base) / SUB) if kind in ("gdrive", "dropbox") else base)


class Sealed:
    """A target for a memory encrypted by Mnemai: what leaves this computer is the encrypted file, never the plain text.

    Mnemai reads its encrypted files as plain text (crypt hooks Path.read_bytes), so without this a synced copy of an
    encrypted memory would land in Google Drive or on a station as plain text. Files the encryption leaves open (pictures,
    PDF, the settings Mnemai needs before the password) go as they are. A station lists hashes of what it stores — the
    encrypted bytes — so the hash of the plain text each one stands for is kept here, next to the sync state."""

    def __init__(self, tgt, vault: Vault, tid: str):
        from . import crypt

        self.t, self.c, self.root = tgt, crypt, vault.root
        self.kid = (crypt.config(vault.root) or {}).get("id", "")
        self.mapf = vault.service / "sync" / f"{tid}.sealed.json"
        try:
            self.map = json.loads(self.mapf.read_text(encoding="utf-8")) if self.mapf.exists() else {}
        except (OSError, ValueError):
            self.map = {}

    def ready(self):
        return self.t.ready()

    def _sealable(self, rel: str) -> bool:
        return bool(self.c.in_scope(self.root / rel))

    def list(self) -> dict[str, str]:
        out = {}
        for rel, h in self.t.list().items():
            m = self.map.get(rel)
            out[rel] = m[1] if m and m[0] == h else h  # a station's hash of the encrypted copy → the plain one
        return out

    def get(self, rel: str) -> bytes:
        data = self.t.get(rel)
        if self.c.is_encrypted_bytes(data):
            plain = self.c.decrypt_bytes(data, rel)  # another password on the other side → Locked, said in the result
            self.map[rel] = [_h(data), _h(plain)]
            return plain
        return data

    def put(self, rel: str, data: bytes) -> None:
        if self._sealable(rel) and not self.c.is_encrypted_bytes(data):
            enc = self.c.encrypt_bytes(self.kid, data)
            self.t.put(rel, enc)
            self.map[rel] = [_h(enc), _h(data)]
        else:
            self.t.put(rel, data)

    def delete(self, rel: str) -> None:
        self.t.delete(rel)
        self.map.pop(rel, None)

    def save(self) -> None:
        self.mapf.parent.mkdir(parents=True, exist_ok=True)
        self.mapf.write_text(json.dumps(self.map), encoding="utf-8")


def _state_file(vault: Vault, tid: str) -> Path:
    return vault.service / "sync" / f"{tid}.json"


# ---------------------------------------------------------------- one pass

APPEND_ONLY = ("90 System/Journal/", "60 Events/")


def union(mine: bytes, theirs: bytes) -> bytes:
    """Journal and events only grow: both devices' lines are kept, this computer's order first."""
    a = mine.decode("utf-8", "replace").splitlines()
    seen = set(a)
    extra = [l for l in theirs.decode("utf-8", "replace").splitlines() if l not in seen]
    return ("\n".join(a + extra) + "\n").encode("utf-8")


def fresh_template(rel: str, data: bytes) -> bool:
    """A file nobody filled in yet (a new computer joining): the other side's version simply wins."""
    from .memory import TEMPLATES

    if rel not in TEMPLATES:
        return False
    norm = lambda t: "\n".join(l for l in t.splitlines() if not l.startswith("updated:")).strip()  # noqa: E731
    return norm(data.decode("utf-8", "replace")) == norm(TEMPLATES[rel].format(today=""))


def conflict_name(rel: str, when: dt.datetime) -> str:
    stem, dot, ext = rel.rpartition(".")
    return f"{stem} (с другого устройства {when:%Y-%m-%d %H-%M}).{ext}"


def sync_target(vault: Vault, t: dict, now: dt.datetime | None = None) -> dict:
    """Three-way sync with one target. Returns what happened."""

    tgt = target_of(vault, t)
    res = {
        "id": t.get("id", ""),
        "kind": t.get("kind"),
        "sent": 0,
        "got": 0,
        "deleted": 0,
        "conflicts": [],
        "error": "",
        "ts": (now or dt.datetime.now()).isoformat(timespec="seconds"),
    }
    if tgt is None:
        res["error"] = "папка облака не найдена на этом компьютере"
        return res
    ok, why = tgt.ready()
    if not ok:
        res["error"] = why
        return res
    from . import crypt

    if crypt.enabled(vault.root):
        if crypt.locked(vault.root):
            res["error"] = "память зашифрована и ещё не открыта паролем"
            return res
        tgt = Sealed(tgt, vault, t.get("id", "x"))
    try:
        _pass(vault, tgt, t, res, now)
    except crypt.Locked:
        res["error"] = "в облаке память, зашифрованная другим паролем"
    finally:
        if isinstance(tgt, Sealed):
            tgt.save()
    return res


def _pass(vault: Vault, tgt, t: dict, res: dict, now: dt.datetime | None) -> None:
    from .journal import log_event, save_copy

    sf = _state_file(vault, t.get("id", "x"))
    state = json.loads(sf.read_text(encoding="utf-8")) if sf.exists() else {}
    loc, rem = local_files(vault.root), tgt.list()
    new_state = {}
    for rel in sorted(set(loc) | set(rem) | set(state)):
        if not wanted(rel):
            continue
        l, r, s = loc.get(rel), rem.get(rel), state.get(rel)
        p = vault.root / rel
        if l == r:
            if l:
                new_state[rel] = l
            continue
        if r == s:  # changed or deleted here only
            if l is None:
                tgt.delete(rel)
                res["deleted"] += 1
            else:
                tgt.put(rel, p.read_bytes())
                res["sent"] += 1
                new_state[rel] = l
        elif l == s:  # changed or deleted there only
            if r is None:
                if p.exists():
                    save_copy(vault, rel, p.read_text(encoding="utf-8", errors="replace"))
                    p.unlink()
                res["deleted"] += 1
            else:
                data = tgt.get(rel)
                if p.exists():
                    save_copy(vault, rel, p.read_text(encoding="utf-8", errors="replace"))
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(data)
                res["got"] += 1
                new_state[rel] = _h(data)
        else:  # changed on both sides (or deleted on one, changed on the other)
            if l is None:  # deleted here, changed there: the change wins
                data = tgt.get(rel)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(data)
                res["got"] += 1
                new_state[rel] = _h(data)
            elif r is None:  # changed here, deleted there: the change wins
                tgt.put(rel, p.read_bytes())
                res["sent"] += 1
                new_state[rel] = l
            else:
                other = tgt.get(rel)
                mine = p.read_bytes()
                if fresh_template(rel, mine):
                    p.write_bytes(other)
                    res["got"] += 1
                    new_state[rel] = _h(other)
                    continue
                if fresh_template(rel, other):
                    tgt.put(rel, mine)
                    res["sent"] += 1
                    new_state[rel] = l
                    continue
                if rel.startswith(APPEND_ONLY):
                    both = union(mine, other)
                    p.write_bytes(both)
                    tgt.put(rel, both)
                    res["got"] += 1
                    new_state[rel] = _h(both)
                    continue
                if rel.startswith(".mnema/"):  # a conversation: the longer one is newer
                    if len(other) > p.stat().st_size:
                        p.write_bytes(other)
                        res["got"] += 1
                        new_state[rel] = _h(other)
                    else:
                        tgt.put(rel, p.read_bytes())
                        res["sent"] += 1
                        new_state[rel] = l
                    continue
                crel = conflict_name(rel, now or dt.datetime.now())
                (vault.root / crel).write_bytes(other)
                tgt.put(rel, p.read_bytes())
                tgt.put(crel, other)
                res["conflicts"].append(crel)
                new_state[rel], new_state[crel] = l, _h(other)
    sf.parent.mkdir(parents=True, exist_ok=True)
    sf.write_text(json.dumps(new_state, ensure_ascii=False), encoding="utf-8")
    if res["sent"] or res["got"] or res["deleted"] or res["conflicts"]:
        log_event(
            vault,
            "sync",
            "write",
            f"синхронизация с {NAMES.get(t.get('kind'), t.get('kind'))}: отправлено {res['sent']}, "
            f"получено {res['got']}, удалено {res['deleted']}, конфликтов {len(res['conflicts'])}",
            res["conflicts"][:20],
        )
    if res["got"] or res["deleted"]:
        from .memory import generate_now

        generate_now(vault)


def run(vault: Vault, only: str = "") -> list[dict]:
    from .learn import settings as S

    if S.load(vault).get("demo"):  # the demo memory never leaves the computer
        return []
    if not _lock.acquire(blocking=False):
        return [{"error": "уже синхронизируется"}]
    try:
        out = []
        targets = settings(vault)["targets"]
        if only:  # a manual pass of one target
            chosen = [t for t in targets if t.get("id") == only]
        else:  # BP-13: one active target at a time — legacy profiles with several on sync the first one
            chosen = [t for t in targets if t.get("on", True)][:1]
        for t in chosen:
            try:
                r = sync_target(vault, t)
            except Exception as e:
                r = {
                    "id": t.get("id"),
                    "kind": t.get("kind"),
                    "error": str(e)[:200],
                    "ts": dt.datetime.now().isoformat(timespec="seconds"),
                }
            _last[f"{vault.root}|{t.get('id')}"] = r
            out.append(r)
        if any(r.get("conflicts") for r in out):
            from . import scribe_cloud

            scribe_cloud.notify(
                "Mnemai: при синхронизации заметка поменялась на двух устройствах — сохранил обе версии"
            )
        return out
    finally:
        _lock.release()


def last(vault: Vault, tid: str) -> dict:
    return _last.get(f"{vault.root}|{tid}", {})


def active(vault: Vault) -> dict | None:
    """The one active target (BP-13: a single active target at a time)."""
    for t in settings(vault)["targets"]:
        if t.get("on", True):
            return t
    return None


def fingerprint(root: Path) -> dict[str, tuple[int, int]]:
    """(rel → (size, mtime_ns)) of the files sync cares about — a cheap change detector, no hashing."""
    out: dict[str, tuple[int, int]] = {}
    if not root.exists():
        return out
    for p in root.rglob("*"):
        if not p.is_file() or not wanted(p.relative_to(root).as_posix()):
            continue
        try:
            st = p.stat()
        except OSError:  # a file gone between the listing and the stat: not a change worth reporting
            continue
        out[p.relative_to(root).as_posix()] = (st.st_size, st.st_mtime_ns)
    return out


def next_delay(results: list[dict], minutes: int) -> float:
    """BP-13: after a pass — 5 minutes when a target was unreachable, else the regular N minutes."""
    if any(r.get("error") for r in results):
        return RETRY_MIN
    return max(1, minutes) * 60


class Syncer(threading.Thread):
    """The owner's schedule (BP-13): one pass soon after the app starts, then on changes at most every
    10 minutes, and a retry in 5 minutes when a target was unreachable. Manual passes go through sync.run."""

    def __init__(self, vault: Vault, first_wait: float = 30.0, poll: float = 15.0):
        super().__init__(daemon=True, name="mnema-sync")
        self.vault = vault
        self.stop_event = threading.Event()
        self.first_wait = first_wait  # the first pass, soon after start
        self.poll = poll  # how often the loop wakes up to notice changes
        self._fp: dict[str, tuple[int, int]] | None = None
        self._last_pass = 0.0
        self._next_run = 0.0

    def stop(self) -> None:
        self.stop_event.set()

    def _changed(self) -> bool:
        """True when a wanted file appeared, changed or disappeared since the previous check."""
        fp = fingerprint(self.vault.root)
        changed = self._fp is not None and fp != self._fp
        self._fp = fp
        return changed

    def run(self) -> None:
        self._fp = fingerprint(self.vault.root)  # the memory as it was when the app started
        self._next_run = time.time() + self.first_wait
        while not self.stop_event.is_set():
            if self.stop_event.wait(self.poll):
                break
            now = time.time()
            if self._changed():  # a change wakes the pass early, but not before the 10-minute cooldown
                self._next_run = min(self._next_run, max(now, self._last_pass + CHANGE_MIN))
            if now < self._next_run:
                continue
            try:
                s = settings(self.vault)
                targets, minutes = s["targets"], max(1, int(s.get("minutes") or 10))
            except Exception:  # locked memory or unreadable profile: retry shortly, the owner may unlock it
                self._last_pass = now
                self._next_run = now + RETRY_MIN
                continue
            if not targets:
                self._next_run = now + 60
                continue
            try:
                results = run(self.vault)
            except Exception:  # noqa: BLE001 — a failed pass must not end the sync loop
                results = []
            self._last_pass = time.time()
            self._fp = fingerprint(self.vault.root)  # what the pass itself wrote is not a change
            self._next_run = self._last_pass + next_delay(results, minutes)


# ---------------------------------------------------------------- setting up targets


def add(vault: Vault, kind: str, path: str = "", url: str = "", token: str = "") -> dict:
    from .agent import profile as P

    if kind not in KINDS:
        raise ValueError("неизвестный способ синхронизации")
    s = settings(vault)
    tid = kind if kind in ("gdrive", "dropbox") else f"{kind}-{int(time.time())}"
    if kind in ("gdrive", "dropbox") and not (path or detected().get(kind)):
        raise ValueError(
            f"{NAMES[kind]} не найден на этом компьютере: установи приложение {NAMES[kind]} и войди в него"
        )
    if kind == "folder" and not path:
        raise ValueError("укажи папку")
    if kind == "station":
        if not url.startswith(("http://", "https://")):
            raise ValueError("адрес станции должен начинаться с https://")
        from .learn import secrets_store
        from .learn.settings import _vid

        secrets_store.put(_vid(vault), "sync.station." + tid, token.strip())
    targets = [{**t, "on": False} for t in s["targets"] if t.get("id") != tid]  # BP-13: one active target at a time
    targets.append({"id": tid, "kind": kind, "path": path, "url": url, "on": True})
    P.save(vault, {"sync": {"targets": targets, "minutes": s["minutes"]}})
    return settings(vault)


def remove(vault: Vault, tid: str) -> dict:
    from .agent import profile as P

    s = settings(vault)
    P.save(vault, {"sync": {"targets": [t for t in s["targets"] if t.get("id") != tid], "minutes": s["minutes"]}})
    _state_file(vault, tid).unlink(missing_ok=True)
    return settings(vault)


def set_minutes(vault: Vault, minutes: int) -> dict:
    from .agent import profile as P

    s = settings(vault)
    P.save(vault, {"sync": {"targets": s["targets"], "minutes": max(1, min(1440, int(minutes)))}})
    return settings(vault)


def public(vault: Vault) -> dict:
    s = settings(vault)
    det = detected()
    return {
        "minutes": s["minutes"],
        "detected": det,
        "targets": [
            {
                **t,
                "name": NAMES.get(t["kind"], t["kind"]),
                "where": t.get("url")
                or t.get("path")
                or (str(Path(det.get(t["kind"]) or "") / SUB) if det.get(t["kind"]) else ""),
                "last": last(vault, t["id"]),
            }
            for t in s["targets"]
        ],
    }
