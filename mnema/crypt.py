"""Mnemai's own encryption of the memory folder, by password, on every system.

What is encrypted: the notes (.md) and the service files that hold what the owner said or did — conversations and
their attachments' text, the journal and its snapshots, learning traces, what went to the clouds, the portrait. Text
files only: binary files (PDF, Word, pictures, recordings) stay as they are, other programs open them. Settings Mnemai
needs before the password (language, models, access rules) stay open too — see PLAIN.

Keys: a random 256-bit memory key encrypts the files (AES-256-GCM). The password, stretched by scrypt, encrypts that
key; both live in .mnema/crypto.json. «Remember on this computer» keeps the memory key in the system's secret store
(DPAPI, Keychain, Secret Service), outside the memory folder: then Mnemai opens without asking, like EFS. A new
password re-encrypts only the key.

File format (text, so a line can be appended — the journal grows that way):
    MNEMA-ENC1 <key id>\\n
    <base64(nonce 12 bytes + ciphertext + tag)>\\n    — one or more records, plaintext is their concatenation

How it hooks in: Path.read_text / read_bytes decrypt any file that starts with the mark (a key for its id must be
open, else Locked); Path.write_text / write_bytes, fsutil.write_atomic and Vault.write_raw encrypt files in scope of
an encrypted folder; journal lines are appended with append_text(). A file written plain by anything else (Obsidian,
an older helper) is readable as before, and seal() encrypts it at the next opening. Encrypting and decrypting the
folder go file by file: each file is written next to itself, checked to read back the same, then swapped in — an
interruption leaves some files done and some not, both readable.
"""

from __future__ import annotations

import base64
import io
import json
import os
import secrets
import threading
from pathlib import Path

MAGIC = b"MNEMA-ENC1 "
RECORD_AAD = b"mnema-file-1"
KEY_AAD = b"mnema-key-1"
SCRYPT = {"n": 2**17, "r": 8, "p": 1}
TEXT = {".md", ".json", ".jsonl", ".txt", ".csv", ".tsv", ".log", ".yml", ".yaml", ".html", ".htm"}
# open without the password: what the program needs to start, show its screens and ask for it
PLAIN = {
    "crypto.json",
    "token",
    "vault_id",
    "write.lock",
    "providers.json",
    "clients.json",
    "agent.json",
    "learn.json",
    "station.json",
    "achievements.json",
    "session.json",
    "learn/cursors.json",
    "learn/next_check",
    "learn/last_check",
    "learn/runs.jsonl",
}
PLAIN_DIRS = ("sync/",)


class Locked(PermissionError):
    """The file is encrypted and its key is not open (no password yet)."""


class BadPassword(ValueError):
    pass


_lock = threading.RLock()
_keys: dict[str, bytes] = {}  # key id → memory key, for the folders opened in this process
_roots: dict[str, str] = {}  # normalised folder path (with a trailing separator) → key id; open or not
_tried: dict[str, float] = {}  # key id → when its key was last looked for


def _norm(p) -> str:
    return os.path.normcase(os.path.abspath(str(p)))


def _forms(root: Path) -> set[str]:
    out = {_norm(root)}
    try:
        out.add(_norm(Path(root).resolve()))
    except OSError:
        pass
    return {f.rstrip("\\/") + os.sep for f in out}


# ---------------------------------------------------------------- raw file IO (never through the hooks)


def _rb(p) -> bytes:
    return _ORIG.get("read_bytes", Path.read_bytes)(Path(p))


def _wb(p, data: bytes) -> None:
    _ORIG.get("write_bytes", Path.write_bytes)(Path(p), data)


# ---------------------------------------------------------------- the key file


def _cfg_path(root: Path) -> Path:
    return Path(root) / ".mnema" / "crypto.json"


def config(root: Path) -> dict | None:
    f = _cfg_path(root)
    try:
        return json.loads(_rb(f).decode("utf-8"))
    except (OSError, ValueError):
        return None


def enabled(root: Path) -> bool:
    return config(root) is not None


def _kek(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

    return Scrypt(salt=salt, length=32, n=n, r=r, p=p).derive(password.encode("utf-8"))


def _wrap(dek: bytes, password: str) -> dict:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    salt, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
    kek = _kek(password, salt, **SCRYPT)
    return {
        "kdf": "scrypt",
        **SCRYPT,
        "salt": base64.b64encode(salt).decode(),
        "key": base64.b64encode(nonce + AESGCM(kek).encrypt(nonce, dek, KEY_AAD)).decode(),
    }


def _unwrap(cfg: dict, password: str) -> bytes:
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    kek = _kek(password, base64.b64decode(cfg["salt"]), int(cfg["n"]), int(cfg["r"]), int(cfg["p"]))
    blob = base64.b64decode(cfg["key"])
    try:
        return AESGCM(kek).decrypt(blob[:12], blob[12:], KEY_AAD)
    except InvalidTag:
        raise BadPassword("пароль не подходит") from None


def _write_cfg(root: Path, cfg: dict) -> None:
    f = _cfg_path(root)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f"crypto.json.{secrets.token_hex(3)}.tmp")
    _wb(tmp, json.dumps(cfg, indent=2).encode("utf-8"))
    os.replace(tmp, f)


# ---------------------------------------------------------------- files


def _seal(key: bytes, data: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = secrets.token_bytes(12)
    return base64.b64encode(nonce + AESGCM(key).encrypt(nonce, data, RECORD_AAD))


def encrypt_bytes(key_id: str, data: bytes) -> bytes:
    key = _keys.get(key_id)
    if key is None:
        raise Locked("память зашифрована, а пароль ещё не введён")
    return MAGIC + key_id.encode() + b"\n" + _seal(key, data) + b"\n"


def decrypt_bytes(data: bytes, where="") -> bytes:
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    head, _, rest = data.partition(b"\n")
    key_id = head[len(MAGIC) :].decode("ascii", "replace").strip()
    key = _keys.get(key_id)
    if key is None:
        raise Locked(f"файл зашифрован, пароль ещё не введён: {where}")
    aead, out = AESGCM(key), []
    for line in rest.split(b"\n"):
        line = line.strip()
        if not line:
            continue
        blob = base64.b64decode(line)
        try:
            out.append(aead.decrypt(blob[:12], blob[12:], RECORD_AAD))
        except InvalidTag:
            raise OSError(f"зашифрованный файл повреждён: {where}") from None
    return b"".join(out)


def is_encrypted_bytes(data: bytes) -> bool:
    return data[: len(MAGIC)] == MAGIC


def _root_of(path) -> tuple[str, str] | None:
    """(folder form, key id) of the encrypted folder this path is in, or None."""
    if not _roots:
        return None
    n = _norm(path)
    for form, kid in _roots.items():
        if n.startswith(form):
            return form, kid
    return None


def in_scope(path) -> str | None:
    """The key id if this file is to be kept encrypted, else None."""
    hit = _root_of(path)
    if not hit:
        return None
    form, kid = hit
    rel = _norm(path)[len(form) :].replace(os.sep, "/")
    if Path(rel).suffix.lower() not in TEXT:
        return None
    if rel.startswith(".mnema/"):
        inner = rel[len(".mnema/") :]
        if inner in PLAIN or inner.startswith(PLAIN_DIRS) or inner.endswith((".lock", ".tmp")):
            return None
    elif rel.startswith(".") or "/." in rel:  # .obsidian, .git, .trash and other tools' folders
        return None
    return kid


# ---------------------------------------------------------------- Path hooks

_ORIG: dict = {}


def _read_bytes(self):
    data = _ORIG["read_bytes"](self)
    return decrypt_bytes(data, self) if data[: len(MAGIC)] == MAGIC else data


def _read_text(self, encoding=None, errors=None, newline=None):
    data = _ORIG["read_bytes"](self)
    if data[: len(MAGIC)] == MAGIC:
        data = decrypt_bytes(data, self)
    enc = io.text_encoding(encoding)
    return io.TextIOWrapper(io.BytesIO(data), encoding=enc, errors=errors, newline=newline).read()


def _encode_text(data: str, encoding=None, errors=None, newline=None) -> bytes:
    buf = io.BytesIO()
    w = io.TextIOWrapper(buf, encoding=io.text_encoding(encoding), errors=errors, newline=newline)
    w.write(data)
    w.flush()
    out = buf.getvalue()
    w.detach()
    return out


def _write_bytes(self, data):
    kid = in_scope(self)
    if kid is None:
        return _ORIG["write_bytes"](self, data)
    raw = bytes(memoryview(data))
    _ORIG["write_bytes"](self, encrypt_bytes(kid, raw))
    return len(raw)


def _write_text(self, data, encoding=None, errors=None, newline=None):
    kid = in_scope(self)
    if kid is None:
        return _ORIG["write_text"](self, data, encoding=encoding, errors=errors, newline=newline)
    if not isinstance(data, str):
        raise TypeError("data must be str, not %s" % data.__class__.__name__)
    _ORIG["write_bytes"](self, encrypt_bytes(kid, _encode_text(data, encoding, errors, newline)))
    return len(data)


def install() -> None:
    """Hook Path once per process. Plain files and paths outside encrypted folders behave exactly as before."""
    with _lock:
        if _ORIG:
            return
        for name in ("read_bytes", "read_text", "write_bytes", "write_text"):
            _ORIG[name] = getattr(Path, name)
        Path.read_bytes = _read_bytes
        Path.read_text = _read_text
        Path.write_bytes = _write_bytes
        Path.write_text = _write_text


def text_for(path: Path, text: str) -> bytes:
    """What fsutil.write_atomic / Vault.write_raw put on disk for this text: encrypted if the file is in scope."""
    raw = text.encode("utf-8")
    kid = in_scope(path)
    return encrypt_bytes(kid, raw) if kid else raw


def _head(path: Path) -> bytes:
    try:
        with open(path, "rb") as fh:
            return fh.readline(200)
    except OSError:
        return b""


def append_text(path: Path, text: str) -> None:
    """Add to a file line by line (the journal): an encrypted file gets one more record; a plain file in scope is
    encrypted whole first; a file out of scope is appended as before."""
    path = Path(path)
    head = _head(path)
    kid = in_scope(path)
    if head.startswith(MAGIC):
        kid = head[len(MAGIC) :].decode("ascii", "replace").strip()
    if not kid:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(text)
        return
    key = _keys.get(kid)
    if key is None:
        raise Locked("память зашифрована, а пароль ещё не введён")
    with _lock:
        if head and not head.startswith(MAGIC):  # a plain file from before: encrypted whole, then appended to
            _atomic(path, encrypt_bytes(kid, _rb(path)))
            head = MAGIC
        with open(path, "ab") as fh:
            if not head:
                fh.write(MAGIC + kid.encode() + b"\n")
            fh.write(_seal(key, text.encode("utf-8")) + b"\n")


def _atomic(path: Path, data: bytes) -> None:
    tmp = path.with_name(f"{path.name}.{secrets.token_hex(3)}.tmp")
    try:
        _wb(tmp, data)
        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


# ---------------------------------------------------------------- opening a folder


def _register(root: Path, kid: str, key: bytes | None) -> None:
    with _lock:
        for f in _forms(Path(root)):
            _roots[f] = kid
        if key is not None:
            _keys[kid] = key


def _secret_id(root: Path) -> str:
    from .learn.secrets_store import vault_id
    from .vault import Vault

    return vault_id(Vault(root))


def attach(root: Path) -> str:
    """Called when a memory folder is opened: "" if it is not encrypted, "open" if its key is here (saved on this
    computer or already given), "locked" if the password is needed."""
    cfg = config(root)
    if not cfg:
        return ""
    install()
    kid = cfg["id"]
    if kid in _keys:
        _register(root, kid, None)
        return "open"
    import time

    last = _tried.get(kid, 0)
    if time.monotonic() - last < 20:  # asked the secret store and the running Mnemai a moment ago
        _register(root, kid, None)
        return "locked"
    _tried[kid] = time.monotonic()
    key = b""
    try:
        from .learn.secrets_store import get

        key = base64.b64decode(get(_secret_id(root), "memory_key") or "")
    except Exception:
        key = b""
    if not key:
        key = _from_running_app(root)
    _register(root, kid, key if len(key) == 32 else None)
    return "open" if len(key) == 32 else "locked"


def _from_running_app(root: Path) -> bytes:
    """The console helper (MCP for Claude Code and others) gets the key from the running Mnemai, which has it."""
    try:
        import urllib.request

        home = Path(os.environ.get("MNEMA_HOME") or Path.home() / ".mnema")
        port = json.loads(_rb(home / "config.json").decode("utf-8")).get("port")
        token = _rb(Path(root) / ".mnema" / "token").decode("utf-8").strip()
        if not port:
            return b""
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/crypto/key", headers={"X-Mnema-Token": token})
        got = json.loads(urllib.request.urlopen(req, timeout=3).read()).get("key", "")
        return base64.b64decode(got) if got else b""
    except Exception:
        return b""


def is_open(root: Path) -> bool:
    cfg = config(root)
    return bool(cfg) and cfg["id"] in _keys


def locked(root: Path) -> bool:
    cfg = config(root)
    return bool(cfg) and cfg["id"] not in _keys


def key_b64(root: Path) -> str:
    cfg = config(root)
    k = _keys.get(cfg["id"]) if cfg else None
    return base64.b64encode(k).decode() if k else ""


def unlock(root: Path, password: str, remember: bool) -> None:
    cfg = config(root)
    if not cfg:
        return
    key = _unwrap(cfg, password)
    _register(root, cfg["id"], key)
    _remember(root, key if remember else None)
    seal(root)


def _remember(root: Path, key: bytes | None) -> None:
    from .learn.secrets_store import put

    put(_secret_id(root), "memory_key", base64.b64encode(key).decode() if key else "")


def remembered(root: Path) -> bool:
    try:
        from .learn.secrets_store import get

        return bool(get(_secret_id(root), "memory_key"))
    except Exception:
        return False


def set_remember(root: Path, on: bool) -> None:
    cfg = config(root)
    if not cfg or cfg["id"] not in _keys:
        raise Locked("сначала введи пароль")
    _remember(root, _keys[cfg["id"]] if on else None)


def change_password(root: Path, old: str, new: str) -> None:
    cfg = config(root)
    if not cfg:
        raise ValueError("память не зашифрована")
    key = _unwrap(cfg, old)
    _check_password(new)
    _write_cfg(root, {"v": 1, "id": cfg["id"], **_wrap(key, new)})


def _check_password(pw: str) -> None:
    if len(pw or "") < 8:
        raise ValueError("пароль — не короче 8 знаков")


# ---------------------------------------------------------------- recovery key

RECOVERY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no I, O, 0, 1: hard to misread or mishear


def _new_recovery() -> str:
    return "-".join("".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(5)) for _ in range(4))


def recover(root: Path, recovery: str, new_password: str) -> dict:
    """A forgotten password is restored only by the recovery key, shown once when encryption was turned on.

    The memory key is unwrapped by the recovery key and re-wrapped by the new password; the recovery key itself
    stays the same and keeps working (the owner's decision, 20.11.2026).
    """
    install()
    cfg = config(root)
    if not cfg:
        raise ValueError("память не зашифрована")
    if "recovery" not in cfg:
        raise ValueError("это шифрование включали без ключа восстановления — пароль восстановить нельзя")
    try:
        key = _unwrap(cfg["recovery"], recovery)
    except BadPassword:
        raise BadPassword("ключ восстановления не подходит") from None
    _check_password(new_password)
    _write_cfg(root, {"v": 1, "id": cfg["id"], "recovery": cfg["recovery"], **_wrap(key, new_password)})
    _register(root, cfg["id"], key)
    return {"files": seal(root)}


# ---------------------------------------------------------------- the whole folder


def _files(root: Path):
    root = Path(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not (d.startswith(".") and d != ".mnema")]
        for name in filenames:
            yield Path(dirpath) / name


def _convert(path: Path, kid: str | None) -> bool:
    """Encrypt (kid) or decrypt (None) one file in place, checked before the swap. True if it changed."""
    raw = _rb(path)
    enc = raw[: len(MAGIC)] == MAGIC
    if kid and not enc:
        new = encrypt_bytes(kid, raw)
        if decrypt_bytes(new, path) != raw:
            raise OSError(f"проверка шифрования не сошлась: {path}")
    elif not kid and enc:
        new = decrypt_bytes(raw, path)
    else:
        return False
    if _rb(path) != raw:  # changed meanwhile: leave it, the next pass takes it
        return False
    _atomic(path, new)
    return True


def seal(root: Path, progress=None) -> int:
    """Encrypt every file in scope that is still plain (written by another program, or left by an interruption)."""
    install()
    cfg = config(root)
    if not cfg or cfg["id"] not in _keys:
        return 0
    n = 0
    for f in _files(root):
        if in_scope(f):
            try:
                n += _convert(f, cfg["id"])
            except OSError:
                continue
            if progress:
                progress(n)
    return n


def enable(root: Path, password: str, remember: bool = True, progress=None) -> dict:
    """Encrypt the memory folder with a new password. Returns {"files": n, "recovery": key}.

    The recovery key is generated here and returned to be shown exactly once; only its wrapped form is stored
    (the owner's decision, 20.11.2026). A forgotten password is restored by recover() and this key only.
    """
    install()
    root = Path(root)
    if enabled(root):
        raise ValueError("память уже зашифрована")
    _check_password(password)
    kid, key = secrets.token_hex(8), secrets.token_bytes(32)
    recovery = _new_recovery()
    _write_cfg(root, {"v": 1, "id": kid, **_wrap(key, password), "recovery": _wrap(key, recovery)})
    _register(root, kid, key)
    if _unwrap(config(root), password) != key:  # the key file reads back before any note is touched
        raise OSError("ключ не записался")
    if remember:
        _remember(root, key)
    return {"files": seal(root, progress), "recovery": recovery}


def disable(root: Path, password: str, progress=None) -> dict:
    """Decrypt everything back to plain files and forget the key."""
    install()
    root = Path(root)
    cfg = config(root)
    if not cfg:
        return {"files": 0}
    key = _unwrap(cfg, password)
    _register(root, cfg["id"], key)
    n = 0
    for f in _files(root):
        if f.name == "crypto.json" or not _peek(f):
            continue
        try:
            n += _convert(f, None)
        except Locked:
            continue
        if progress:
            progress(n)
    left = [f for f in _files(root) if f.name != "crypto.json" and _peek(f)]
    if left:
        raise OSError(f"не все файлы расшифровались ({len(left)}), шифрование оставлено: попробуй ещё раз")
    _remember(root, None)
    _cfg_path(root).unlink(missing_ok=True)
    with _lock:
        for form in [f for f, k in _roots.items() if k == cfg["id"]]:
            _roots.pop(form, None)
    return {"files": n}


def _peek(f: Path) -> bool:
    try:
        with open(f, "rb") as fh:
            return fh.read(len(MAGIC)) == MAGIC
    except OSError:
        return False


def status(root: Path) -> dict:
    cfg = config(root)
    if not cfg:
        return {"on": False}
    enc = sum(1 for f in _files(root) if _peek(f))
    return {"on": True, "open": cfg["id"] in _keys, "files": enc, "remembered": remembered(root)}


def selftest() -> bool:
    """The built program's check that encryption is packed whole: a key from a password, a file there and back."""
    kid = "selftest"
    try:
        _keys[kid] = b"k" * 32
        w = _wrap(b"k" * 32, "selftest password")
        return _unwrap(w, "selftest password") == b"k" * 32 and decrypt_bytes(encrypt_bytes(kid, b"mnema")) == b"mnema"
    except Exception:
        return False
    finally:
        _keys.pop(kid, None)
