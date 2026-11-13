"""Stage official Windows releases in the background; install only after a normal exit.

Source trees, portable copies and other platforms never self-modify. The installer
owns file replacement. No tokens, accounts or third-party update service are used.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import threading
import urllib.parse
import urllib.request
from pathlib import Path

from . import __version__

REPO = "Pumpetee/Mnemai"
LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
INTERVAL = 6 * 60 * 60
MAX_INSTALLER = 1024 * 1024 * 1024
LOG = logging.getLogger(__name__)


def version(value: str) -> tuple[int, int, int]:
    if not re.fullmatch(r"v?\d+\.\d+\.\d+", value):
        raise ValueError("Not a stable version")
    return tuple(int(n) for n in value.removeprefix("v").split("."))


def installed_dir() -> Path | None:
    """Only an Inno-installed, frozen Windows app is eligible, never a source run."""
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return None
    app = Path(sys.executable).resolve().parent
    if Path(sys.executable).name.lower() != "mnemai.exe" or not (app / "unins000.dat").is_file():
        return None
    return app


def enabled(config: dict) -> bool:
    return config.get("auto_update", True) is True and os.environ.get("MNEMA_NO_UPDATE") != "1"


def hold_cli_install_lock():
    """Keep bundled MCP/CLI runtimes safe from replacement until their process exits."""
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return None
    import ctypes
    from ctypes import wintypes

    create = ctypes.windll.kernel32.CreateMutexW
    create.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    create.restype = wintypes.HANDLE
    handle = create(None, False, "Local\\MnemaiCliInUse")
    if not handle:
        raise ctypes.WinError()
    return handle  # Windows closes it on process exit; the launcher retains it meanwhile


def _trusted_url(url: str) -> bool:
    u = urllib.parse.urlsplit(url)
    return (
        u.scheme == "https"
        and u.hostname
        in {"api.github.com", "github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"}
        and u.port in (None, 443)
        and not u.username
        and not u.password
    )


class _Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _trusted_url(newurl):
            raise ValueError("Untrusted update redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open(url: str):
    from . import net

    if not _trusted_url(url):
        raise ValueError("Untrusted update URL")
    req = urllib.request.Request(
        url, headers={"User-Agent": f"Mnemai/{__version__}", "Accept": "application/vnd.github+json"}
    )
    proxy = net.proxy()
    handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy} if proxy else {})
    return urllib.request.build_opener(handler, _Redirect()).open(req, timeout=30)


def _read(url: str, limit: int) -> bytes:
    with _open(url) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Update metadata too large")
    return data


def _asset_url(asset: dict, tag: str) -> str:
    url = asset["browser_download_url"]
    expected = f"https://github.com/{REPO}/releases/download/{tag}/{asset['name']}"
    if url != expected:
        raise ValueError("Asset is not from the official release")
    return url


def release(data: dict, current: str = __version__) -> tuple[dict, str] | None:
    """Select a versioned installer, never a mutable 'latest' alias or prerelease."""
    tag = data.get("tag_name", "")
    if data.get("draft") or data.get("prerelease") or version(tag) <= version(current):
        return None
    name = f"Mnemai-Setup-{tag.removeprefix('v')}.exe"
    assets = data.get("assets", [])
    asset = next((a for a in assets if a.get("name") == name and a.get("state") == "uploaded"), None)
    if not asset or not 0 < asset.get("size", 0) <= MAX_INSTALLER:
        return None
    _asset_url(asset, tag)
    digest = asset.get("digest") or ""
    if re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
        return asset, digest[7:].lower()
    checksum = next((a for a in assets if a.get("name") == name + ".sha256"), None)
    if not checksum:
        raise ValueError("Release has no SHA-256")
    text = _read(_asset_url(checksum, tag), 4096).decode("utf-8").strip()
    match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?" + re.escape(name), text)
    if not match:
        raise ValueError("Invalid release checksum")
    return asset, match[1].lower()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(asset: dict, digest: str, cache: Path, stop: threading.Event) -> Path:
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / asset["name"]
    if target.is_file() and target.stat().st_size == asset["size"] and sha256(target) == digest:
        return target
    partial = target.with_suffix(".part")
    try:
        with _open(asset["browser_download_url"]) as response, partial.open("wb") as f:
            size = 0
            while chunk := response.read(1024 * 1024):
                if stop.is_set():
                    raise InterruptedError("Update download stopped")
                size += len(chunk)
                if size > asset["size"]:
                    raise ValueError("Installer exceeds published size")
                f.write(chunk)
        if size != asset["size"] or sha256(partial) != digest:
            raise ValueError("Installer size or SHA-256 mismatch")
        partial.replace(target)
        return target
    finally:
        partial.unlink(missing_ok=True)


def _quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def install_script(installer: Path, digest: str, app: Path, pid: int) -> str:
    """The helper outlives the app, waits for its exit, then rechecks the file.

    An update never force-closes a window or an active recording. Install errors
    stay in update-install.log; the next session can retry the cached download.
    """
    exe, setup = _quote(str(app / "Mnemai.exe")), _quote(str(installer))
    args = [
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/SP-",
        "/AUTOUPDATE=1",
        f'/DIR="{app}"',
        f'/LOG="{installer.parent / "update-install.log"}"',
    ]
    return f"""$ErrorActionPreference = 'Stop'
try {{
  $parent = $null
  try {{ $parent = [Diagnostics.Process]::GetProcessById({pid}) }} catch [ArgumentException] {{ }}
  if ($parent -and -not $parent.WaitForExit(300000)) {{ exit 1 }}
  $file = [IO.File]::OpenRead({setup})
  $sha = [Security.Cryptography.SHA256]::Create()
  try {{ $hash = [BitConverter]::ToString($sha.ComputeHash($file)).Replace('-', '') }}
  finally {{ $file.Dispose(); $sha.Dispose() }}
  if ($hash -ne {_quote(digest)}) {{ exit 2 }}
  $info = New-Object Diagnostics.ProcessStartInfo
  $info.FileName = {setup}
  $info.Arguments = {_quote(' '.join(args))}
  $info.UseShellExecute = $false
  $info.CreateNoWindow = $true
  $p = [Diagnostics.Process]::Start($info)
  $p.WaitForExit()
  if ($p.ExitCode -ne 0) {{ exit $p.ExitCode }}
  try {{ [IO.File]::Delete({setup}) }} catch {{ }}
  $info.FileName = {exe}
  $info.Arguments = '--hidden'
  $info.WorkingDirectory = {_quote(str(app))}
  [Diagnostics.Process]::Start($info) | Out-Null
}} catch {{ exit 1 }}
"""


class Updater:
    def __init__(self, home: Path, config):
        self.home, self.config = home, config
        self.stop = threading.Event()
        self.pending: tuple[Path, str] | None = None
        self.thread: threading.Thread | None = None

    def start(self):
        if installed_dir() and enabled(self.config()):
            self.thread = threading.Thread(target=self._run, daemon=True, name="mnemai-updates")
            self.thread.start()

    def _run(self):
        # Let the window and local server start before making any network request.
        if self.stop.wait(30):
            return
        while not self.stop.is_set() and enabled(self.config()):
            try:
                found = release(json.loads(_read(LATEST, 1024 * 1024)))
                if found:
                    asset, digest = found
                    path = download(asset, digest, self.home / "updates", self.stop)
                    self.pending = path, digest
                    return
            except Exception as e:  # update failure must never stop the desktop app
                LOG.info("Update deferred (%s)", type(e).__name__)
            if self.stop.wait(INTERVAL):
                return

    def on_exit(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=2)
        app = installed_dir()
        if not self.pending or not app or not enabled(self.config()):
            return
        installer, digest = self.pending
        script = install_script(installer, digest, app, os.getpid())
        encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        # System executable, never one from the current directory or PATH.
        powershell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
        subprocess.Popen(
            [str(powershell), "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            close_fds=True,
            cwd=str(self.home),
        )
