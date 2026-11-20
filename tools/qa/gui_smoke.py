"""The built program opens its window and serves the memory — on the system it runs on (CI: Windows, macOS, Linux).

    python tools/qa/gui_smoke.py <path to Mnemai program> <path to mnemai-cli>
    python tools/qa/gui_smoke.py --source        # the same from the source tree

A throw-away home and memory folder; the program starts as the owner would start it (window, tray), must write its
port, answer on it with its token, serve the interface, keep the tray, read text from a picture (OCR packed whole)
and log no error. Then it is stopped.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if sys.argv[1] == "--source":
    app, cli = [sys.executable, "-m", "mnema.desktop"], [sys.executable, "-m", "mnema"]
else:
    app, cli = [str(Path(sys.argv[1]).resolve())], [str(Path(sys.argv[2]).resolve())]
tmp = Path(tempfile.mkdtemp(prefix="mnema-gui-"))
home, memory = tmp / "home", tmp / "memory"
env = dict(os.environ, MNEMA_HOME=str(home), MNEMA_NO_DETECT="1", MNEMA_NO_KEYRING="1")
subprocess.run([*cli, "init", str(memory), "--default"], check=True, env=env, timeout=120, cwd=ROOT)
home.mkdir(parents=True, exist_ok=True)
(home / "config.json").write_text(
    json.dumps({"vault": str(memory), "lang": "en", "on_close": "quit"}), encoding="utf-8"
)
token = (memory / ".mnema" / "token").read_text(encoding="utf-8").strip()

proc = subprocess.Popen(app, env=env, cwd=ROOT)
ok, why = False, "the program wrote no port"
try:
    for _ in range(120):
        time.sleep(1)
        if proc.poll() is not None:
            why = f"the program exited with code {proc.returncode}"
            break
        try:
            port = json.loads((home / "config.json").read_text(encoding="utf-8")).get("port")
        except (OSError, ValueError):
            port = None
        if not port:
            continue
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/api/ping", headers={"X-Mnema-Token": token})
            ping = json.loads(urllib.request.urlopen(req, timeout=3).read())
            page = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5).read().decode("utf-8")
        except OSError as e:
            why = f"port {port} does not answer: {e}"
            continue
        if ping.get("ok") and "<html" in page.lower():
            time.sleep(8)  # the window and the tray settle; a crash shows up in the log
            ok, why = proc.poll() is None, f"version {ping.get('version')}, port {port}"
            req = urllib.request.Request(f"http://127.0.0.1:{port}/api/app/selftest", headers={"X-Mnema-Token": token})
            st = json.loads(urllib.request.urlopen(req, timeout=120).read())
            seen = st.get("ocr", "")
            if "1427" in seen:
                why += ", reads scans"
            else:
                ok, why = False, why + f", but scan recognition does not work in the build (read: {seen!r})"
            if st.get("crypt"):
                why += ", encrypts"
            else:
                ok, why = False, why + ", but encryption does not work in the build"
            if st.get("telegram"):
                why += ", carries Telegram"
            else:
                ok, why = False, why + ", but Telegram is missing from the build"
            if ok:  # «Выход», as from the tray: the program must really end, not hang without a window
                req = urllib.request.Request(f"http://127.0.0.1:{port}/api/app/quit", headers={"X-Mnema-Token": token})
                urllib.request.urlopen(req, timeout=5).read()
                try:
                    proc.wait(timeout=30)
                    why += ", quits cleanly"
                except subprocess.TimeoutExpired:
                    ok, why = False, why + ", but HANGS on quit (still running 30 s after «Выход»)"
            break
finally:
    log = home / "app.log"
    text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    proc.terminate()
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()

if text.strip():
    print(text[-4000:])
    first = " / ".join(line.strip() for line in text.strip().splitlines()[:3])[:400]
    ok, why = False, why + f"; errors in app.log: {first}"
print(("OK " if ok else "FAIL ") + why, flush=True)
if not ok:  # GitHub parses this line and shows the reason in the run's annotations even without the raw log
    print(f"::error title=Mnemai window smoke::{why}", flush=True)
sys.exit(0 if ok else 1)
