"""What differs between Windows, macOS and Linux (mnema/osapi.py) — checked on whichever system runs the tests."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mnema import osapi as OS  # noqa: E402


class OsApi(unittest.TestCase):
    def test_program_names(self):
        self.assertEqual(OS.exe("llama-server"), "llama-server.exe" if sys.platform == "win32" else "llama-server")

    def test_interface_names_this_system(self):
        text = "Ключи в хранилище Windows · Как в Windows · WindowsXP"
        with mock.patch.object(OS, "IS_WIN", True):
            self.assertEqual(OS.os_words(text), text)
        with mock.patch.object(OS, "IS_WIN", False), mock.patch.object(OS, "IS_MAC", True):
            self.assertEqual(OS.os_words(text), "Ключи в хранилище macOS · Как в macOS · WindowsXP")
        with mock.patch.object(OS, "IS_WIN", False), mock.patch.object(OS, "IS_MAC", False):
            self.assertEqual(OS.os_words(text), "Ключи в хранилище Linux · Как в Linux · WindowsXP")

    def test_settings_folders_of_other_programs(self):
        p = OS.config_dir("Claude", "claude_desktop_config.json")
        self.assertEqual(p.name, "claude_desktop_config.json")
        self.assertEqual(p.parent.name, "Claude")
        if sys.platform == "darwin":
            self.assertIn("Application Support", str(p))

    def test_memory_size_is_known(self):
        total, avail = OS.ram()
        self.assertGreater(total, 0)
        self.assertGreaterEqual(total, avail)

    def test_quiet_child_process(self):
        kw = OS.quiet()
        if sys.platform == "win32":
            self.assertIn("creationflags", kw)
        else:
            self.assertEqual(kw, {})

    @unittest.skipIf(sys.platform == "win32", "Windows keeps it in the registry")
    def test_start_at_login_file(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"HOME": d, "XDG_CONFIG_HOME": d}):
            self.assertFalse(OS.autostart_enabled())
            OS.set_autostart(True)
            self.assertTrue(OS.autostart_enabled())
            f = OS._mac_agent() if sys.platform == "darwin" else OS._linux_entry()
            self.assertIn("--hidden", f.read_bytes().decode("utf-8"))
            OS.set_autostart(False)
            self.assertFalse(OS.autostart_enabled())

    @unittest.skipIf(sys.platform == "win32", "Windows uses a named mutex")
    def test_one_copy_at_a_time(self):
        with tempfile.TemporaryDirectory() as d:
            import fcntl

            self.assertTrue(OS.first_instance(Path(d)))
            with open(Path(d) / "app.lock", "w") as other:  # a second copy can't take the lock
                with self.assertRaises(OSError):
                    fcntl.flock(other.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            for h in list(getattr(OS, "_instance", [])):  # the held instance lock must not leak a file handle
                try:
                    h.close()
                except OSError:
                    pass
            OS._instance.clear()

    def test_keys_without_a_system_store_stay_in_the_owner_file(self):
        from mnema.learn import secrets_store as S

        with (
            tempfile.TemporaryDirectory() as d,
            mock.patch.dict(os.environ, {"MNEMA_HOME": d, "MNEMA_NO_KEYRING": "1"}),
        ):
            S.put("id:test", "api", "sk-123")
            self.assertEqual(S.get("id:test", "api"), "sk-123")
            raw = (Path(d) / "secrets.json").read_text(encoding="utf-8")
            self.assertNotIn("store:", raw)
            S.put("id:test", "api", "")
            self.assertEqual(S.get("id:test", "api"), "")


if __name__ == "__main__":
    unittest.main()
