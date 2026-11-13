"""Memory switched off: AIs get nothing about the owner, nothing is written — chat and everything else still work."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mnema.agent import profile as P  # noqa: E402
from mnema.chat import engine as CH, tools as TL  # noqa: E402
from mnema.learn import engine as LE  # noqa: E402
from mnema.learn.sources import Episode  # noqa: E402
from mnema.mcp_server import Server  # noqa: E402
from mnema.memory import init_vault, remember  # noqa: E402
from mnema.vault import Vault  # noqa: E402


def _vault(on: bool) -> Vault:
    v = Vault(Path(tempfile.mkdtemp()))
    init_vault(v)
    remember(v, "SECRETFACT пилот в ноябре", "decisions")
    P.save(v, {"memory_on": on})
    return v


class MemorySwitch(unittest.TestCase):
    def test_existing_memory_stays_on(self):
        v = Vault(Path(tempfile.mkdtemp()))
        init_vault(v)
        self.assertTrue(P.memory_on(v))  # a folder from before the switch: nothing disappears

    def test_off_no_memory_in_the_request(self):
        on, off = _vault(True), _vault(False)
        self.assertIn("SECRETFACT", CH.system_prompt(on, "anthropic", log=False))
        prompt = CH.system_prompt(off, "anthropic", log=False)
        self.assertNotIn("SECRETFACT", prompt)
        self.assertIn("Память Mnemai выключена", prompt)

    def test_off_mcp_gives_nothing_and_writes_nothing(self):
        v = _vault(False)
        s = Server(v, "claude")
        self.assertIn("выключена", s.call("memory_context", {}))
        self.assertIn("выключена", s.call("memory_remember", {"fact": "NEWFACT"}))
        self.assertNotIn("NEWFACT", v.read_raw("00 Inbox/Inbox.md") or "")

    def test_off_learning_writes_nothing(self):
        v = _vault(False)
        rep = LE.learn_episodes(v, [Episode("mnema_chat", "c#1", "", "Запомни: NEWFACT живу в Казани")], "mnema_chat")
        self.assertEqual(rep.get("written", 0), 0)
        self.assertEqual(LE.run(v), {"skipped": "память выключена"})

    def test_off_actions_have_no_memory_folder_and_no_remember(self):
        v = _vault(False)
        self.assertEqual(TL.roots(v), [])
        self.assertTrue(TL.enabled(v))  # the terminal still works without the memory folder
        self.assertTrue(TL.pc_enabled(v))
        P.save(v, {"pc_access": False})
        self.assertFalse(TL.enabled(v))  # no memory folder, no work folders, no terminal: nowhere to act
        work = Path(tempfile.mkdtemp())
        P.save(v, {"pc_access": True, "tool_folders": [str(work)]})
        self.assertTrue(TL.enabled(v))
        with self.assertRaises(TL.Refused):
            TL.run(v, {"tool": "remember", "body": "NEWFACT"})
        with self.assertRaises(TL.Refused):
            TL.resolve(v, str(v.root / "00 Inbox" / "Inbox.md"))

    def test_turning_on_brings_it_back(self):
        v = _vault(False)
        P.save(v, {"memory_on": True, "memory_asked": True})
        self.assertIn("SECRETFACT", CH.system_prompt(v, "anthropic", log=False))
        self.assertTrue(P.load(v)["memory_asked"])


if __name__ == "__main__":
    unittest.main()
