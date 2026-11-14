"""Claude Code gets Mnemai's MCP server: the config points at this vault and no native tools are allowed."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())

from mnema.chat import providers as PR  # noqa: E402
from mnema.memory import init_vault  # noqa: E402
from mnema.vault import Vault  # noqa: E402


class ClaudeMcp(unittest.TestCase):
    def test_config_points_at_this_vault(self):
        v = Vault(Path(tempfile.mkdtemp()) / "v")
        init_vault(v)
        cfg = PR._claude_mcp_config(v)
        data = json.loads(cfg.read_text(encoding="utf-8"))
        srv = data["mcpServers"]["mnemai"]
        self.assertEqual(srv["command"], sys.executable)
        self.assertEqual(srv["args"][:2], ["-m", "mnema"])
        self.assertIn("--vault", srv["args"])
        self.assertEqual(srv["args"][srv["args"].index("--vault") + 1], str(v.root))
        self.assertIn("mcp", srv["args"])
        self.assertTrue(Path(srv["env"]["PYTHONPATH"]).is_dir())
        self.assertIn("MCP", PR.CLAUDE_MCP_NOTE)


if __name__ == "__main__":
    unittest.main()
