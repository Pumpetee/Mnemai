"""Meetings: this computer or the cloud Whisper, decided by speed and settings; the owner is told. Fake audio only."""

import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from mnema import scribe, scribe_cloud as SC  # noqa: E402
from mnema.agent import profile as P  # noqa: E402
from mnema.learn import secrets_store  # noqa: E402
from mnema.learn.settings import _vid  # noqa: E402
from mnema.memory import init_vault  # noqa: E402
from mnema.vault import Vault  # noqa: E402

CALLS = []


class Whisper(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        CALLS.append(
            {
                "path": self.path,
                "auth": self.headers.get("Authorization"),
                "size": len(body),
                "model": b'name="model"\r\n\r\nwhisper-test' in body,
            }
        )
        out = json.dumps(
            {"text": "привет", "segments": [{"start": 1.0, "end": 3.0, "text": "Привет, начнём встречу."}]}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


class Base(unittest.TestCase):
    def setUp(self):
        CALLS.clear()
        self.dir = Path(tempfile.mkdtemp())
        self.v = Vault(self.dir)
        init_vault(self.v)
        self.srv = HTTPServer(("127.0.0.1", 0), Whisper)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        P.save(
            self.v, {"scribe_base": f"http://127.0.0.1:{self.srv.server_port}/v1", "scribe_cloud_model": "whisper-test"}
        )
        secrets_store.put(_vid(self.v), "scribe.cloud", "test-key")

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        shutil.rmtree(self.dir, ignore_errors=True)


class TestCloud(Base):
    def test_long_audio_goes_in_pieces_on_one_time_line(self):
        audio = np.zeros(SC.SR * 25 * 60, dtype=np.float32)  # 25 minutes → 3 pieces
        segs = SC.cloud_transcribe(self.v, audio, "Я")
        self.assertEqual(len(CALLS), 3)
        self.assertTrue(
            all(
                c["path"] == "/v1/audio/transcriptions" and c["auth"] == "Bearer test-key" and c["model"] for c in CALLS
            )
        )
        self.assertTrue(all(c["size"] < 25 * 1024 * 1024 for c in CALLS))
        self.assertEqual([s["start"] for s in segs], [1.0, 601.0, 1201.0])
        self.assertIn("whisper", (self.dir / ".mnema" / "outgoing.jsonl").read_text(encoding="utf-8"))

    def test_fits(self):
        self.assertTrue(SC.fits(500, 60))  # ten minutes is always fine
        self.assertTrue(SC.fits(3000, 3600))  # faster than the meeting itself
        self.assertFalse(SC.fits(7200, 3600))


class TestDecision(Base):
    """The whole flow with a slow fake computer: where it goes and what the owner is told."""

    def run_meeting(self, mode, rtf=2.0):
        P.save(self.v, {"scribe_mode": mode})
        d = self.dir / "meet"
        d.mkdir()
        f = d / "запись.wav"
        f.write_bytes(b"0" * 10000)
        orig = (SC.load, SC.measure, scribe._whisper, scribe.transcribe)
        sent = {}
        from mnema.chat import engine as CH

        orig_send = CH.send
        SC.load = lambda p: np.zeros(SC.SR * 30 * 60, dtype=np.float32)  # 30 minutes
        SC.measure = lambda m, a: (rtf, [])
        scribe._whisper = lambda name, threads=0: object()
        scribe.transcribe = lambda m, a, label, progress=None: (
            [{"start": 0.0, "end": 2.0, "speaker": label, "text": "Локально распознано"}],
            1800.0,
        )
        CH.send = lambda vault, text, **kw: sent.update(kw) or {"chat": "c1"}
        try:
            scribe._launch(self.v, d, "Планёрка", [(f, "Запись")], 0, "")
            s = scribe.st(self.v)
            for _ in range(100):
                if s.get("status") in ("done", "error"):
                    break
                time.sleep(0.05)
            return dict(s), (d / "Расшифровка.md").read_text(encoding="utf-8") if (
                d / "Расшифровка.md"
            ).exists() else ""
        finally:
            SC.load, SC.measure, scribe._whisper, scribe.transcribe = orig
            CH.send = orig_send

    def test_fast_sends_long_to_cloud_and_says_so(self):
        s, md = self.run_meeting("fast")
        self.assertEqual((s["status"], s["where"]), ("done", "cloud"))
        self.assertIn("отдаю облачному Whisper", s["notice"])
        self.assertIn("распознано облачным Whisper", md)

    def test_quality_with_key_goes_to_cloud(self):
        s, md = self.run_meeting("quality")
        self.assertEqual((s["status"], s["where"]), ("done", "cloud"))
        self.assertIn("пресет Quality", s["notice"])
        self.assertIn("распознано облачным Whisper", md)

    def test_private_stays_local_even_on_a_slow_computer(self):
        s, md = self.run_meeting("private", rtf=2.0)
        self.assertEqual((s["status"], s["where"]), ("done", "local"))
        self.assertEqual(CALLS, [])  # nothing left the computer
        self.assertIn("распознано на этом компьютере", md)

    def test_audio_is_removed_unless_kept(self):
        s, _ = self.run_meeting("private")
        self.assertEqual(s["status"], "done")
        self.assertFalse((self.dir / "meet" / "запись.wav").exists())
        self.assertTrue((self.dir / "meet" / "Расшифровка.md").exists())
        shutil.rmtree(self.dir / "meet")
        P.save(self.v, {"scribe_keep_audio": True})
        self.run_meeting("private")
        self.assertTrue((self.dir / "meet" / "запись.wav").exists())

    def test_fast_computer_stays_local_without_asking(self):
        s, _ = self.run_meeting("fast", rtf=0.2)
        self.assertEqual((s["status"], s["where"]), ("done", "local"))
        self.assertIn("Расшифровываю на компьютере, примерно 6 мин", s["notices"])
        self.assertEqual(P.load(self.v)["scribe_rtf"], 0.2)


if __name__ == "__main__":
    unittest.main()
