"""mcp_call: одно «да» на вызов, «Да для этого разговора» разрешает его на разговор.

mcp_smoke / mcp_smoke_readonly / mcp_smoke_all остаются строгим FORCE_ASK: одно «да» на каждый прогон,
«Да для этого разговора» к ним не применяется. В другом чате mcp_call спрашивается заново.
"""

import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())  # never touch the real home
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mnema.agent import profile as P  # noqa: E402
from mnema.chat import engine as CH  # noqa: E402
from mnema.chat import providers as PR  # noqa: E402
from mnema.memory import init_vault  # noqa: E402
from mnema.vault import Vault  # noqa: E402


def _vault() -> Vault:
    v = Vault(Path(tempfile.mkdtemp()))
    init_vault(v)
    PR.save(v, "openai", models=["m1"], key="sk-test-0000000000000000")
    P.save(v, {"tools_ask": True})
    return v


class Script:
    """A fake model: each call answers with the next reply."""

    def __init__(self, *replies):
        self.replies = list(replies)

    def __call__(self, vault, pid, model, system, messages, stop=None, usage=None, meta=None, **kw):
        yield self.replies.pop(0) if self.replies else "Готово."


class Owner:
    """Answers the permission card in a thread, like a click: yes | no | always."""

    def __init__(self, choices):
        self.choices, self.asked = list(choices), []
        threading.Thread(target=self.loop, daemon=True).start()

    def loop(self):
        end = time.time() + 30
        while time.time() < end and self.choices:
            for cid, g in list(CH._gen.items()):
                p = g.get("pending")
                if p:
                    self.asked.append(p["tool"])
                    CH.answer_action(cid, p["id"], self.choices.pop(0))
            time.sleep(0.05)


CALL = '```mnema mcp_call name="clients_list"\n{}\n```'
SMOKE = "```mnema mcp_smoke_all\n```"


class McpAskTest(unittest.TestCase):
    def setUp(self):
        self.old = PR.stream

    def tearDown(self):
        PR.stream = self.old

    def _send(self, v, text, script, choices, cid=""):
        PR.stream = script
        owner = Owner(choices)
        with mock.patch("mnema.mcp_server.run_action", return_value=("ок", "ок", "")):
            r = CH.send(v, text, cid=cid, model="openai:m1", learn=False, sync=True)
        time.sleep(0.3)
        return r, owner

    def test_mcp_call_always_is_not_asked_again_in_the_same_chat(self):
        v = _vault()
        s = Script(CALL, CALL, "Готово.")
        r, owner = self._send(v, "Два вызова", s, ["always"])
        self.assertEqual(owner.asked, ["mcp_call"])  # спросили один раз, второй пошёл без карточки
        self.assertIn("mcp_call", CH.load_chat(v, r["chat"]).get("tools_ok") or [])

    def test_mcp_call_yes_still_asks_every_time(self):
        v = _vault()
        s = Script(CALL, CALL, "Готово.")
        r, owner = self._send(v, "Два вызова", s, ["yes", "yes"])
        self.assertEqual(owner.asked, ["mcp_call", "mcp_call"])
        self.assertNotIn("mcp_call", CH.load_chat(v, r["chat"]).get("tools_ok") or [])

    def test_mcp_call_asks_again_in_another_chat(self):
        v = _vault()
        r1, owner1 = self._send(v, "Первый чат", Script(CALL, "Готово."), ["always"])
        self.assertEqual(owner1.asked, ["mcp_call"])
        r2, owner2 = self._send(v, "Второй чат", Script(CALL, "Готово."), ["yes"])
        self.assertEqual(owner2.asked, ["mcp_call"])  # в другом чате разрешение не действует
        self.assertNotIn("mcp_call", CH.load_chat(v, r2["chat"]).get("tools_ok") or [])

    def test_mcp_smoke_all_still_asks_every_time(self):
        v = _vault()
        s = Script(SMOKE, SMOKE, "Готово.")
        r, owner = self._send(v, "Два прогона", s, ["always", "yes"])
        self.assertEqual(owner.asked, ["mcp_smoke_all", "mcp_smoke_all"])  # «always» прогон не разрешает
        self.assertNotIn("mcp_smoke_all", CH.load_chat(v, r["chat"]).get("tools_ok") or [])


if __name__ == "__main__":
    unittest.main()
