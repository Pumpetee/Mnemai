import os
import json
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())  # never touch the real home
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mnema.api import make_server  # noqa: E402
from mnema.memory import init_vault, token  # noqa: E402
from mnema.vault import Vault  # noqa: E402
from test_core import fill  # noqa: E402
from hidden_topics import lock_cloud  # noqa: E402


class TestApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = Path(tempfile.mkdtemp())
        cls.v = Vault(cls.dir)
        init_vault(cls.v)
        fill(cls.v)
        cls.srv = make_server(cls.v, 0)  # port 0 → free port
        cls.port = cls.srv.server_address[1]
        # rebuild with the real port so the Host check matches
        cls.srv.server_close()
        cls.srv = make_server(cls.v, cls.port)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.tok = token(cls.v)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        shutil.rmtree(cls.dir, ignore_errors=True)

    def req(self, path, data=None, tok=True, host=None):
        r = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            method="POST" if data is not None else "GET",
            data=json.dumps(data, ensure_ascii=False).encode("utf-8") if data is not None else None,
        )
        if tok:
            r.add_header("X-Mnema-Token", tok if isinstance(tok, str) else self.tok)
        r.add_header("Content-Type", "application/json")
        if host:
            r.add_header("Host", host)
        try:
            with urllib.request.urlopen(r, timeout=10) as resp:
                body = resp.read().decode("utf-8")
                return resp.status, (json.loads(body) if "json" in resp.headers.get("Content-Type", "") else body)
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    def test_learning_api(self):
        from mnema.learn import engine
        from mnema.learn.sources import Episode

        code, _ = self.req("/api/learn/settings", {"sources": {"mnema_chat": {"enabled": True, "mode": "quiet"}}})
        self.assertEqual(code, 200)
        engine.learn_episodes(
            self.v,
            [Episode("mnema_chat", "c1#1", "", "Запомни, что я играю в теннис по четвергам.", prev="Чем могу помочь?")],
            "mnema_chat",
        )
        self.assertIn("теннис по четвергам", self.v.read_raw("00 Inbox/Inbox.md"))
        items = self.req("/api/learn/items?view=learned")[1]["items"]
        it = next(i for i in items if "теннис" in i["text"])
        # undo in the journal = "no": the fact is rejected and won't come back
        ev = next(e for e in self.req("/api/journal")[1] if e["action"] == "write" and "теннис" in e["summary"])
        self.assertEqual(self.req("/api/undo", {"id": ev["id"]})[0], 200)
        rej = self.req("/api/learn/items?view=rejected")[1]["items"]
        self.assertIn(it["id"], [i["id"] for i in rej])
        self.assertNotIn("теннис", self.v.read_raw("00 Inbox/Inbox.md"))
        status = self.req("/api/learn/status")[1]
        self.assertIn("claude_code", status["sources"])
        self.assertNotIn("browser", status["sources"])  # the browser extension is gone
        self.assertEqual(self.req("/api/learn/review", {"id": "nope", "action": "keep"})[0], 400)

    def test_one_token_and_no_browser_door(self):
        # the browser extension (removed 24.10.2026) had its own token and routes: none of them is left
        (self.v.service / "ext_token").write_text("old-extension-token", encoding="utf-8")
        self.assertEqual(self.req("/api/ping", tok="old-extension-token")[0], 401)
        self.assertEqual(self.req("/api/ext_token")[0], 404)
        self.assertNotEqual(self.req("/api/observe", {"client": "chatgpt", "text": "x"})[0], 200)
        self.assertNotEqual(self.req("/api/extension/open", {})[0], 200)

    def test_reveal_a_path_outside_memory(self):
        """«Показать в папке» under an action may point outside the memory roots (a `claude` binary, a log)."""
        from unittest.mock import patch

        from mnema import osapi

        outside = Path(tempfile.mkdtemp()) / "outside.md"
        outside.write_text("x", encoding="utf-8")
        try:
            with patch.object(osapi, "reveal", lambda p: None), patch.object(osapi, "open_path", lambda p: None):
                code, body = self.req("/api/files/reveal", {"path": str(outside)})
            self.assertEqual(code, 200)
            self.assertTrue(body["ok"])
        finally:
            shutil.rmtree(outside.parent, ignore_errors=True)

    def test_token_required(self):
        code, _ = self.req("/api/now", tok=False)
        self.assertEqual(code, 401)

    def test_bad_host_blocked(self):
        code, _ = self.req("/api/now", host="evil.example:7461")
        self.assertEqual(code, 403)
        code, _ = self.req("/", host="evil.example")
        self.assertEqual(code, 403)

    def test_ui_has_token(self):
        code, html = self.req("/")
        self.assertEqual(code, 200)
        self.assertIn(self.tok, html)
        self.assertNotIn("__MNEMA_TOKEN__", html)

    def test_context_respects_client(self):
        lock_cloud(self.v)
        code, d = self.req("/api/context?client=chatgpt")
        self.assertEqual(code, 200)
        self.assertNotIn("100к", d["text"])
        _, d = self.req("/api/context?client=claude")
        self.assertIn("100к", d["text"])

    def test_note_paths(self):
        self.assertEqual(self.req("/api/note?rel=70%20Memory/Profile.md")[0], 200)
        for bad in (
            ".mnema/token",
            "../x.md",
            "10%20Now.md",
            "20%20Projects/../../x.md",
            "95%20Saves/x.md",
            "90%20System/Journal/x.md",
        ):
            self.assertEqual(self.req("/api/note?rel=" + bad)[0], 400, bad)
        self.assertEqual(self.req("/api/note", {"rel": ".mnema/clients.json", "raw": "[]"})[0], 400)

    def test_remember_permissions_and_undo(self):
        code, d = self.req("/api/remember", {"fact": "через API", "where": "rules", "client": "chatgpt"})
        self.assertEqual(code, 403)
        code, d = self.req("/api/remember", {"fact": "через API", "client": "chatgpt"})
        self.assertEqual(code, 200)
        self.assertIn("через API", self.v.read_raw("00 Inbox/Inbox.md"))
        code, _ = self.req("/api/undo", {"id": d["id"]})
        self.assertEqual(code, 200)
        self.assertNotIn("через API", self.v.read_raw("00 Inbox/Inbox.md"))

    def test_clients_roundtrip(self):
        _, cl = self.req("/api/clients")
        gem = next(c for c in cl if c["id"] == "gemini")
        gem["enabled"] = False
        self.assertEqual(self.req("/api/clients", cl)[0], 200)
        _, d = self.req("/api/context?client=gemini")
        self.assertEqual(d["text"], "")
        gem["enabled"] = True
        self.req("/api/clients", cl)


if __name__ == "__main__":
    unittest.main()
