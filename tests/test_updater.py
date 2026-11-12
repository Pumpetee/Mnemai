"""Official release selection, fail-closed downloads and the Windows handoff."""

import base64
import copy
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from email.message import Message
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
from urllib.response import addinfourl

from mnema import updater as U

DATA = b"a complete installer"
DIGEST = hashlib.sha256(DATA).hexdigest()


def official():
    name = "Mnemai-Setup-2.4.0.exe"
    asset = {
        "name": name,
        "state": "uploaded",
        "size": len(DATA),
        "digest": "sha256:" + DIGEST,
        "browser_download_url": f"https://github.com/{U.REPO}/releases/download/v2.4.0/{name}",
    }
    return {"tag_name": "v2.4.0", "assets": [asset], "draft": False, "prerelease": False}


class UpdaterTest(unittest.TestCase):
    def test_versions_are_numeric_and_stable_only(self):
        self.assertGreater(U.version("v2.10.0"), U.version("2.9.9"))
        for bad in ("2.4.0-beta", "main", "2.4", "../../2.4.0", ""):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                U.version(bad)

    def test_selects_official_versioned_asset(self):
        asset, digest = U.release(official(), "2.3.1")
        self.assertEqual(asset["name"], "Mnemai-Setup-2.4.0.exe")
        self.assertEqual(digest, DIGEST)

    def test_ignores_old_draft_prerelease_missing_and_oversize(self):
        for field, value in (("draft", True), ("prerelease", True), ("assets", [])):
            data = official()
            data[field] = value
            self.assertIsNone(U.release(data))
        self.assertIsNone(U.release(official(), "2.4.0"))
        self.assertIsNone(U.release(official(), "3.0.0"))
        for size in (0, -1, U.MAX_INSTALLER + 1):
            data = official()
            data["assets"][0]["size"] = size
            self.assertIsNone(U.release(data))

    def test_rejects_foreign_asset_even_with_valid_hash(self):
        for url in ("https://example.org/setup.exe", "http://github.com/setup.exe"):
            data = official()
            data["assets"][0]["browser_download_url"] = url
            with self.assertRaises(ValueError):
                U.release(data)

    def test_checksum_fallback_binds_filename(self):
        data = official()
        asset = data["assets"][0]
        asset.pop("digest")
        checksum = copy.deepcopy(asset)
        checksum["name"] += ".sha256"
        checksum["browser_download_url"] += ".sha256"
        data["assets"].append(checksum)
        with patch.object(U, "_read", return_value=f"{DIGEST}  {asset['name']}\n".encode()):
            self.assertEqual(U.release(data)[1], DIGEST)
        for text in (DIGEST, f"{DIGEST}  another.exe", "corrupt"):
            with patch.object(U, "_read", return_value=text.encode()), self.assertRaises(ValueError):
                U.release(data)
        data["assets"].pop()
        with self.assertRaises(ValueError):
            U.release(data)

    def test_redirect_rejects_http_foreign_hosts_and_credentials(self):
        for url in (
            "http://github.com/x",
            "https://evil.github.com/x",
            "https://github.com.evil.org/x",
            "https://user:password@github.com/x",
            "https://github.com:444/x",
        ):
            self.assertFalse(U._trusted_url(url))
            with self.assertRaises(ValueError):
                U._Redirect().redirect_request(None, None, 302, "", {}, url)
        self.assertTrue(U._trusted_url("https://release-assets.githubusercontent.com/x?download=1"))

    def test_metadata_limit(self):
        with patch.object(U, "_open", return_value=io.BytesIO(b"12345")), self.assertRaises(ValueError):
            U._read(U.LATEST, 4)

    def test_download_verifies_and_reuses_cache(self):
        # Value: protects=only verified installer bytes may survive cache reuse/recovery;
        # fails_when=corrupt cache is trusted or not replaced atomically;
        # why_new=existing test covered only valid cache reuse; seam=none.
        with tempfile.TemporaryDirectory() as root:
            cache = Path(root)
            asset, digest = U.release(official())
            with patch.object(U, "_open", return_value=io.BytesIO(DATA)) as request:
                path = U.download(asset, digest, cache, threading.Event())
                self.assertEqual(path.read_bytes(), DATA)
                self.assertEqual(U.download(asset, digest, cache, threading.Event()), path)
                request.assert_called_once()
            path.write_bytes(b"x" * len(DATA))
            with patch.object(U, "_open", return_value=io.BytesIO(DATA)) as request:
                self.assertEqual(U.download(asset, digest, cache, threading.Event()).read_bytes(), DATA)
                request.assert_called_once()
            self.assertFalse(list(cache.glob("*.part")))

    def test_actual_opener_accepts_official_redirect_and_rejects_foreign_redirect(self):
        # Value: protects=the real urllib opener enforces the redirect trust boundary;
        # fails_when=the allowlist handler is omitted or valid redirect processing breaks;
        # why_new=direct redirect rejection tests did not exercise opener registration; seam=none.
        seen = []
        responses = []
        location = "https://release-assets.githubusercontent.com/official-installer"

        class Transport(U.urllib.request.HTTPSHandler):
            def https_open(self, req):
                seen.append(req)
                headers = Message()
                redirected = req.full_url == U.LATEST
                if redirected:
                    headers["Location"] = location
                response = addinfourl(
                    io.BytesIO(b"" if redirected else DATA), headers, req.full_url, 302 if redirected else 200
                )
                response.msg = "Found" if redirected else "OK"
                responses.append(response)
                return response

        with patch.object(U.urllib.request, "HTTPSHandler", Transport):
            with U._open(U.LATEST) as response:
                self.assertEqual(response.read(), DATA)
            self.assertEqual([request.full_url for request in seen], [U.LATEST, location])
            self.assertEqual(seen[0].get_header("User-agent"), f"Mnemai/{U.__version__}")
            location = "https://example.org/installer"
            seen.clear()
            with self.assertRaises(ValueError):
                U._open(U.LATEST)
            self.assertEqual(len(seen), 1)
        for response in responses:
            response.close()

    def test_opener_honors_configured_proxy_and_explicit_direct_mode(self):
        # Value: protects=updates obey the application's selected network route;
        # fails_when=urllib implicitly chooses system settings instead of net.proxy;
        # why_new=redirect transport fixtures do not inspect the proxy contract; seam=none.
        from mnema import net

        for proxy in ("http://127.0.0.1:65501", ""):
            with (
                self.subTest(proxy=proxy),
                patch.object(net, "proxy", return_value=proxy),
                patch.object(U.urllib.request, "build_opener") as build,
            ):
                U._open(U.LATEST)
                handlers = build.call_args.args
                route = next(h.proxies for h in handlers if isinstance(h, U.urllib.request.ProxyHandler))
                self.assertEqual(route, {"http": proxy, "https": proxy} if proxy else {})
                self.assertTrue(any(isinstance(h, U._Redirect) for h in handlers))

    @unittest.skipUnless(sys.platform == "win32", "Windows CLI mutex")
    def test_bundled_cli_holds_named_installation_mutex(self):
        # Value: protects=bundled MCP runtime stays marked in-use for installer deferral;
        # fails_when=CLI lock is absent or source/non-Windows runs acquire it;
        # why_new=desktop lifecycle tests do not run Windows CLI installation lock; seam=none.
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.windll.kernel32
        kernel.OpenMutexW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
        kernel.OpenMutexW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        with patch.object(U.sys, "frozen", False, create=True):
            self.assertIsNone(U.hold_cli_install_lock())
        with patch.object(U.sys, "frozen", True, create=True), patch.object(U.sys, "platform", "linux"):
            self.assertIsNone(U.hold_cli_install_lock())
        with patch.object(U.sys, "frozen", True, create=True):
            handle = U.hold_cli_install_lock()
        try:
            observed = kernel.OpenMutexW(0x100000, False, "Local\\MnemaiCliInUse")
            self.assertTrue(observed)
            kernel.CloseHandle(observed)
        finally:
            kernel.CloseHandle(handle)

    def test_corruption_short_long_cancelled_and_network_failure_leave_no_partial(self):
        for body in (b"short", b"x" * len(DATA), DATA + b"extra", DATA):
            with self.subTest(body=body), tempfile.TemporaryDirectory() as root:
                asset, digest = U.release(official())
                stop = threading.Event()
                if body == DATA:
                    stop.set()
                with (
                    patch.object(U, "_open", return_value=io.BytesIO(body)),
                    self.assertRaises((ValueError, InterruptedError)),
                ):
                    U.download(asset, digest, Path(root), stop)
                self.assertFalse(list(Path(root).iterdir()))
        with tempfile.TemporaryDirectory() as root:
            with patch.object(U, "_open", side_effect=OSError), self.assertRaises(OSError):
                U.download(asset, digest, Path(root), threading.Event())
            self.assertFalse(list(Path(root).iterdir()))

    def test_source_and_portable_never_start_network_worker(self):
        with tempfile.TemporaryDirectory() as root:
            exe = Path(root) / "Mnemai.exe"
            exe.touch()
            with patch.object(U.sys, "platform", "win32"), patch.object(U.sys, "executable", str(exe)):
                with patch.object(U.sys, "frozen", False, create=True):
                    self.assertIsNone(U.installed_dir())
                with patch.object(U.sys, "frozen", True, create=True):
                    self.assertIsNone(U.installed_dir())
                    (Path(root) / "unins000.dat").touch()
                    self.assertEqual(U.installed_dir(), Path(root).resolve())

    def test_disabled_never_checks_or_installs(self):
        with patch.object(U, "installed_dir", return_value=Path("app")), patch.object(U.threading, "Thread") as thread:
            updater = U.Updater(Path("home"), lambda: {"auto_update": False})
            updater.start()
            updater.pending = Path("setup.exe"), DIGEST
            with patch.object(U.subprocess, "Popen") as launch:
                updater.on_exit()
                launch.assert_not_called()
            thread.assert_not_called()
        with patch.dict(os.environ, {"MNEMA_NO_UPDATE": "1"}):
            self.assertFalse(U.enabled({}))

    def test_worker_stages_without_installing(self):
        with tempfile.TemporaryDirectory() as root:
            updater = U.Updater(Path(root), lambda: {})
            updater.stop = Mock()
            updater.stop.wait.return_value = False
            updater.stop.is_set.return_value = False
            with (
                patch.object(U, "_read", return_value=json.dumps(official()).encode()),
                patch.object(U, "download", return_value=Path(root) / "setup.exe"),
                patch.object(U.subprocess, "Popen") as launch,
            ):
                updater._run()
                self.assertEqual(updater.pending[1], DIGEST)
                launch.assert_not_called()

    def test_network_failure_retries_later_without_installing(self):
        updater = U.Updater(Path("home"), lambda: {})
        updater.stop = Mock()
        updater.stop.wait.side_effect = [False, True]
        updater.stop.is_set.return_value = False
        with patch.object(U, "_read", side_effect=OSError):
            updater._run()
        self.assertIsNone(updater.pending)
        updater.stop.wait.assert_called_with(U.INTERVAL)

    def test_worker_start_polls_current_release_and_stops_before_network_when_cancelled(self):
        # Value: protects=eligible daemon polls without installation and cancellation avoids network;
        # fails_when=start is disconnected, no-release polling stops, or startup cancellation is ignored;
        # why_new=existing worker tests invoked only staging/error paths directly; seam=none.
        updater = U.Updater(Path("home"), lambda: {})
        waits = []
        stopped = threading.Event()

        class FastStop:
            def set(self):
                stopped.set()

            def is_set(self):
                return stopped.is_set()

            def wait(self, timeout):
                waits.append(timeout)
                return stopped.is_set()

        updater.stop = FastStop()
        current = official()
        current["tag_name"] = U.__version__
        calls = []

        def latest(*args):
            calls.append(args)
            if len(calls) == 2:
                updater.stop.set()
            return json.dumps(current).encode()

        with patch.object(U, "installed_dir", return_value=Path("app")), patch.object(U, "_read", side_effect=latest):
            updater.start()
            updater.thread.join(timeout=2)
            self.assertFalse(updater.thread.is_alive())
            self.assertTrue(updater.thread.daemon)
            self.assertEqual(len(calls), 2)
            self.assertEqual(waits, [30, U.INTERVAL, U.INTERVAL])
            self.assertIsNone(updater.pending)
            with patch.object(U, "_read") as request:
                updater._run()
                request.assert_not_called()

    @unittest.skipUnless(sys.platform == "win32", "Windows handoff")
    def test_exit_waits_for_worker_completion_before_scheduling_install(self):
        # Value: protects=shutdown joins a finishing worker before consuming its verified result;
        # fails_when=exit skips cancellation/join or reads pending before the worker finishes;
        # why_new=existing exit tests used no active worker; seam=none.
        updater = U.Updater(Path("home"), lambda: {})
        entered = threading.Event()

        def finishing_download():
            entered.set()
            updater.stop.wait(2)
            updater.pending = Path("cache/setup.exe"), DIGEST

        updater.thread = threading.Thread(target=finishing_download)
        updater.thread.start()
        self.assertTrue(entered.wait(1))
        with patch.object(U, "installed_dir", return_value=Path("app")), patch.object(U.subprocess, "Popen") as launch:
            updater.on_exit()
            self.assertFalse(updater.thread.is_alive())
            self.assertTrue(updater.stop.is_set())
            launch.assert_called_once()
            script = base64.b64decode(launch.call_args.args[0][-1]).decode("utf-16le")
            self.assertIn(DIGEST, script)

    def test_desktop_lifecycle_hands_off_after_normal_window_exit_only(self):
        # Value: protects=desktop starts updates before the loop and installs only after normal loop exit;
        # fails_when=lifecycle hooks are removed/reordered or a window crash triggers installation;
        # why_new=updater unit tests never executed App.run; seam=none.
        from mnema import desktop

        for crash in (False, True):
            with self.subTest(crash=crash):
                events = []
                updater = Mock()
                updater.start.side_effect = lambda: events.append("updater-start")
                updater.on_exit.side_effect = lambda: events.append("updater-exit")

                def window_loop(**kwargs):
                    events.append("window-loop")
                    if crash:
                        raise RuntimeError("window failed")

                with (
                    patch.object(desktop, "load_config", return_value={}),
                    patch.object(desktop, "start_screen", return_value="setup"),
                    patch.object(desktop, "setup_html", return_value="<html></html>"),
                    patch.object(desktop, "windows_dark", return_value=False),
                    patch.object(desktop.App, "build_tray"),
                    patch.object(desktop.webview, "create_window", return_value=MagicMock()),
                    patch.object(desktop.webview, "start", side_effect=window_loop),
                    patch("mnema.cli.migrate_mcp"),
                    patch.object(U, "Updater", return_value=updater),
                ):
                    app = desktop.App(hidden=False)
                    if crash:
                        with self.assertRaises(RuntimeError):
                            app.run()
                    else:
                        app.run()
                self.assertEqual(events, ["updater-start", "window-loop"] + ([] if crash else ["updater-exit"]))

    @unittest.skipUnless(sys.platform == "win32", "Windows helper")
    def test_exit_launches_hidden_encoded_helper_only_when_ready(self):
        updater = U.Updater(Path("home"), lambda: {})
        with patch.object(U, "installed_dir", return_value=Path("app")), patch.object(U.subprocess, "Popen") as launch:
            updater.on_exit()
            launch.assert_not_called()
            updater.pending = Path("cache/setup.exe"), DIGEST
            updater.on_exit()
            args, kwargs = launch.call_args
            script = base64.b64decode(args[0][-1]).decode("utf-16le")
            self.assertIn("/AUTOUPDATE=1", script)
            self.assertIn("WaitForExit", script)
            self.assertIn("SHA256", script)
            self.assertTrue(kwargs["creationflags"] & subprocess.CREATE_NO_WINDOW)

    @unittest.skipUnless(sys.platform == "win32", "Windows helper integration")
    def test_real_helper_success_bad_hash_and_installer_failure(self):
        compiler = Path(os.environ.get("SystemRoot", "C:/Windows")) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
        if not compiler.is_file():
            self.skipTest(".NET Framework compiler unavailable")
        # Value: protects=real PowerShell wait/hash/install/relaunch contract;
        # fails_when=quoting breaks or failed/unverified installers relaunch;
        # why_new=mocked Popen does not execute the helper; seam=none.
        with tempfile.TemporaryDirectory(prefix="Mnemai user's ") as root:
            folder = Path(root)
            source = folder / "fixture.cs"
            source.write_text(
                'using System; using System.IO; using System.Reflection; '
                'class Fixture { static int Main(string[] args) { '
                'var path = Assembly.GetExecutingAssembly().Location; '
                'File.WriteAllLines(path + ".args", args); '
                'return File.Exists(path + ".fail") ? 9 : 0; } }',
                encoding="utf-8",
            )
            installer = folder / "setup.exe"
            subprocess.run(
                [str(compiler), "/nologo", "/target:winexe", f"/out:{installer}", str(source)],
                check=True,
                capture_output=True,
            )
            exe = folder / "Mnemai.exe"
            exe.write_bytes(installer.read_bytes())
            digest = U.sha256(installer)
            ps = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
            for mode, expected in (("bad_hash", 2), ("failed_installer", 9), ("success", 0)):
                with self.subTest(mode=mode):
                    (folder / "setup.exe.args").unlink(missing_ok=True)
                    (folder / "Mnemai.exe.args").unlink(missing_ok=True)
                    fail = folder / "setup.exe.fail"
                    fail.unlink(missing_ok=True)
                    if mode == "failed_installer":
                        fail.touch()
                    parent = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.5)"])
                    script = U.install_script(installer, "0" * 64 if mode == "bad_hash" else digest, folder, parent.pid)
                    encoded = base64.b64encode(script.encode("utf-16le")).decode()
                    result = subprocess.run(
                        [str(ps), "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                        capture_output=True,
                        timeout=30,
                    )
                    parent.wait(timeout=5)
                    self.assertEqual(result.returncode, expected, result.stderr.decode(errors="replace"))
                    if mode == "bad_hash":
                        self.assertFalse((folder / "setup.exe.args").exists())
                    else:
                        args = (folder / "setup.exe.args").read_text().splitlines()
                        self.assertIn("/AUTOUPDATE=1", args)
                        self.assertIn(f"/DIR={folder}", args)
                        self.assertIn("/NORESTART", args)
                    if mode == "success":
                        import time

                        deadline = time.monotonic() + 5
                        while not (folder / "Mnemai.exe.args").exists() and time.monotonic() < deadline:
                            time.sleep(0.05)
                        self.assertEqual((folder / "Mnemai.exe.args").read_text().strip(), "--hidden")
                        self.assertFalse(installer.exists())
                    else:
                        self.assertFalse((folder / "Mnemai.exe.args").exists())
                        self.assertTrue(installer.exists())


if __name__ == "__main__":
    unittest.main()
