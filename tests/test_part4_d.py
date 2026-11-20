"""Часть 4, область D: расписание синка, одна активная цель, пароль станции, удаление папки после остановки синка.

Decisions of the owner (20.11.2026, BP-13/BP-16): sync runs at start, on changes at most every 10 minutes
and manually; an unreachable target is retried in 5 minutes; one active target at a time; the tray shows an
indicator; the station accepts the owner's password (no roles); a memory folder is deleted only after the app
closed it and the sync stopped, with no undo.
"""

import base64
import datetime as dt
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import types
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mnema import station, sync  # noqa: E402
from mnema.memory import init_vault, remember  # noqa: E402
from mnema.vault import Vault  # noqa: E402

TODAY = dt.date(2026, 10, 18)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.v = Vault(self.tmp / "M")
        init_vault(self.v)
        self.cloud = self.tmp / "cloud"
        self.cloud.mkdir()
        sync.add(self.v, "folder", path=str(self.cloud / "Mnemai"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestOneActiveTarget(Base):
    def test_adding_a_target_turns_the_previous_one_off(self):
        first = sync.settings(self.v)["targets"][0]
        self.assertTrue(first["on"])
        time.sleep(1.1)  # a target id carries the second it was made in: two adds in one second collide
        sync.add(self.v, "folder", path=str(self.tmp / "second" / "Mnemai"))
        targets = sync.settings(self.v)["targets"]
        self.assertEqual(len(targets), 2)
        self.assertFalse(next(t for t in targets if t["id"] == first["id"])["on"])
        self.assertTrue(next(t for t in targets if t["id"] != first["id"])["on"])
        self.assertEqual(sync.active(self.v)["id"], targets[-1]["id"])

    def test_run_syncs_only_the_active_target(self):
        other = self.tmp / "second"
        other.mkdir()
        time.sleep(1.1)  # see above: two adds in one second collide
        sync.add(self.v, "folder", path=str(other / "Mnemai"))
        remember(self.v, "Только активная цель", "card:Тест", today=TODAY)
        for r in sync.run(self.v):
            self.assertEqual(r.get("error", ""), "")
        self.assertTrue((other / "Mnemai" / "70 Memory/Cards/Тест.md").exists())
        self.assertFalse((self.cloud / "Mnemai" / "70 Memory/Cards/Тест.md").exists())


class TestFingerprintAndDelay(Base):
    def test_fingerprint_sees_a_change_and_skips_generated_files(self):
        fp0 = sync.fingerprint(self.v.root)
        self.assertNotIn("10 Now.md", fp0)
        remember(self.v, "Свежий факт", "card:Тест", today=TODAY)
        fp1 = sync.fingerprint(self.v.root)
        self.assertNotEqual(fp0, fp1)

    def test_next_delay_retry_is_five_minutes_on_error(self):
        self.assertEqual(sync.next_delay([{"error": "папки нет"}], 10), sync.RETRY_MIN)
        self.assertEqual(sync.next_delay([{"error": "станция не отвечает"}], 30), 300)

    def test_next_delay_is_the_regular_minutes_when_ok(self):
        self.assertEqual(sync.next_delay([], 10), 600)
        self.assertEqual(sync.next_delay([{"error": "", "sent": 1}], 30), 1800)


class TestSyncerSchedule(Base):
    def test_pass_on_start_and_again_on_change_with_the_cooldown(self):
        with mock.patch.object(sync, "CHANGE_MIN", 0.6):
            s = sync.Syncer(self.v, first_wait=0.4, poll=0.2)
            s.start()
            try:
                remember(self.v, "Факт один", "card:Тест", today=TODAY)
                card = self.cloud / "Mnemai" / "70 Memory/Cards/Тест.md"
                deadline = time.time() + 8
                while time.time() < deadline and not card.exists():
                    time.sleep(0.2)
                self.assertTrue(card.exists())
                remember(self.v, "Факт два", "card:Тест", today=TODAY)
                deadline = time.time() + 8
                while time.time() < deadline and "Факт два" not in card.read_text(encoding="utf-8"):
                    time.sleep(0.2)
                self.assertIn("Факт два", card.read_text(encoding="utf-8"))
            finally:
                s.stop()
                s.join(5)
                self.assertFalse(s.is_alive())

    def test_unreachable_target_is_retried_in_five_minutes(self):
        with mock.patch.object(sync, "RETRY_MIN", 0.4), mock.patch.object(sync, "CHANGE_MIN", 600):
            shutil.rmtree(self.cloud)  # the target's parent disappears: every pass fails
            s = sync.Syncer(self.v, first_wait=0.4, poll=0.2)
            s.start()
            try:
                tid = sync.active(self.v)["id"]
                deadline = time.time() + 8
                while time.time() < deadline and not sync.last(self.v, tid).get("error"):
                    time.sleep(0.2)
                self.assertIn("папки нет", sync.last(self.v, tid).get("error", ""))
                self.cloud.mkdir()  # the target is back: the 5-minute retry (patched) picks it up
                remember(self.v, "Снова тут", "card:Тест", today=TODAY)
                card = self.cloud / "Mnemai" / "70 Memory/Cards/Тест.md"
                deadline = time.time() + 8
                while time.time() < deadline and not card.exists():
                    time.sleep(0.2)
                self.assertTrue(card.exists())
            finally:
                s.stop()
                s.join(5)
                self.assertFalse(s.is_alive())


class TestStationPassword(unittest.TestCase):
    PASSWORD = "пароль-владельца"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.sv = Vault(self.tmp / "S")
        station.set_password(self.sv, self.PASSWORD)
        self.srv = station.make_server(self.sv, "127.0.0.1", 0)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_port}"

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _get(self, path: str, bearer: str):
        req = urllib.request.Request(self.url + path, headers={"Authorization": f"Bearer {bearer}"})
        return urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req)

    def test_sync_works_with_the_owners_password(self):
        v = Vault(self.tmp / "M")
        init_vault(v)
        remember(v, "Пилот — пароль", "card:Работа", today=TODAY)
        sync.add(v, "station", url=self.url, token=self.PASSWORD)
        r = sync.run(v)[0]
        self.assertEqual(r.get("error", ""), "")
        self.assertTrue((self.sv.root / "70 Memory/Cards/Работа.md").exists())

    def test_wrong_password_is_rejected(self):
        with self.assertRaises(Exception):
            self._get("/sync/list", "неверный")

    def test_no_password_is_rejected(self):
        with self.assertRaises(Exception):
            urllib.request.build_opener(urllib.request.ProxyHandler({})).open(self.url + "/sync/list")

    def test_legacy_sync_key_keeps_working(self):
        k = station.keys(self.sv)["sync"]
        data = json.loads(self._get("/sync/list", k).read())
        self.assertIsInstance(data, dict)
        self.assertIn("70 Memory/Profile.md", data)

    def test_mcp_with_the_password_serves_the_owner(self):
        b64 = base64.urlsafe_b64encode(self.PASSWORD.encode("utf-8")).decode("ascii")
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}).encode()
        req = urllib.request.Request(
            self.url + "/mcp",
            data=body,
            method="POST",
            headers={"Authorization": f"Bearer {b64}", "Content-Type": "application/json"},
        )
        r = json.loads(urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req).read())
        self.assertEqual(r["result"]["serverInfo"]["name"], "mnemai")


class TestDesktopSyncLifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.v = Vault(self.tmp / "M")
        init_vault(self.v)
        from mnema import desktop as D  # noqa: PLC0415 — MNEMA_HOME is set before the import

        self.D = D
        self.app = D.App(True)

    def tearDown(self):
        self.app._stop_sync()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_sync_starts_with_the_vault_and_stops(self):
        self.app._start_sync(self.v)
        s = self.app.syncer
        self.assertIsNotNone(s)
        self.assertTrue(s.is_alive())
        self.app._stop_sync()
        self.assertIsNone(self.app.syncer)
        s.join(5)
        self.assertFalse(s.is_alive())

    def test_deleting_the_open_folder_stops_sync_first(self):
        self.app.vault = self.v
        self.app.server = None
        self.app.learner = None
        self.app.window = types.SimpleNamespace(load_html=lambda html: None)
        self.app._start_sync(self.v)
        s = self.app.syncer
        trashed = []

        def to_trash(p):
            self.assertIsNone(self.app.syncer)  # BP-16: the folder goes only after the sync stopped
            trashed.append(p)
            return True

        with mock.patch("mnema.osapi.to_trash", to_trash):
            self.app._close_and_delete(self.v.root, None)
        self.assertIn(self.v.root, trashed)
        self.assertIsNone(self.app.vault)
        s.join(5)
        self.assertFalse(s.is_alive())

    def test_tray_menu_has_a_sync_action_and_an_indicator(self):
        self.app.vault = self.v
        cloud = self.tmp / "cloud"
        cloud.mkdir()
        sync.add(self.v, "folder", path=str(cloud / "Mnemai"))
        sync.run(self.v)
        items = self.app.menu_items()
        labels = [it[0] for it in items if isinstance(it, tuple)]
        self.assertIn("Синхронизировать сейчас", labels)
        texts = [l() for l in labels if callable(l) and not isinstance(l, str)]
        indicator = next(t for t in texts if t.startswith("Синхронизация:"))
        self.assertIn("Своя папка", indicator)


if __name__ == "__main__":
    unittest.main()
