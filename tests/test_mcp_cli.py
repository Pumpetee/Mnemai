import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())  # never touch the real home
sys.path.insert(0, str(REPO))

from mnema.agent import profile as P  # noqa: E402
from mnema.memory import init_vault, remember  # noqa: E402
from mnema.vault import Vault  # noqa: E402
from test_core import fill  # noqa: E402
from hidden_topics import lock_cloud  # noqa: E402

ENV = {**os.environ, "PYTHONPATH": str(REPO), "PYTHONUTF8": "1"}


def run_cli(*args, vault=None):
    cmd = [sys.executable, "-m", "mnema"] + (["--vault", str(vault)] if vault else []) + list(args)
    return subprocess.run(cmd, capture_output=True, env=ENV, cwd=str(REPO))


class TestMcp(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        v = Vault(self.dir)
        init_vault(v)
        fill(v)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def session(self, client, messages):
        p = subprocess.run(
            [sys.executable, "-m", "mnema", "--vault", str(self.dir), "mcp", "--client", client],
            input="\n".join(json.dumps(m, ensure_ascii=False) for m in messages).encode("utf-8") + b"\n",
            capture_output=True,
            env=ENV,
            cwd=str(REPO),
            timeout=60,
        )
        return [json.loads(l) for l in p.stdout.decode("utf-8").splitlines() if l.strip()]

    def test_handshake_and_tools(self):
        r = self.session(
            "claude",
            [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "t", "version": "1"},
                    },
                },
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "memory_context", "arguments": {}},
                },
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {"name": "memory_remember", "arguments": {"fact": "Встреча в пн", "where": "decisions"}},
                },
                {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {"name": "memory_search", "arguments": {"query": "встреча"}},
                },
                {"jsonrpc": "2.0", "id": 6, "method": "nope"},
                {
                    "jsonrpc": "2.0",
                    "id": 7,
                    "method": "tools/call",
                    "params": {"name": "memory_stale", "arguments": {}},
                },
            ],
        )
        self.assertEqual(len(r), 7)  # notification gets no reply
        self.assertEqual(r[0]["result"]["protocolVersion"], "2025-06-18")
        self.assertEqual(r[0]["result"]["serverInfo"]["name"], "mnemai")
        self.assertEqual({t["name"] for t in r[1]["result"]["tools"]} >= {"memory_context", "memory_remember"}, True)
        self.assertIn("Иван", r[2]["result"]["content"][0]["text"])
        self.assertFalse(r[3]["result"]["isError"])
        self.assertIn("Встреча в пн", r[4]["result"]["content"][0]["text"])
        self.assertEqual(r[5]["error"]["code"], -32601)
        self.assertIn("Доход", r[6]["result"]["content"][0]["text"])  # claude may see money

    def test_pc_tools_over_mcp(self):
        target = self.dir / "pc-note.txt"
        r = self.session(
            "claude",
            [
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "pc_run", "arguments": {"command": "echo mcp-pc-ok"}},
                },
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "pc_write_file", "arguments": {"path": str(target), "text": "привет"}},
                },
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {"name": "pc_read_file", "arguments": {"path": str(target)}},
                },
                {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {"name": "pc_list_dir", "arguments": {"path": str(self.dir)}},
                },
                {
                    "jsonrpc": "2.0",
                    "id": 6,
                    "method": "tools/call",
                    "params": {"name": "pc_open_app", "arguments": {"name": "definitely-not-installed-app-xyz"}},
                },
            ],
        )
        names = {t["name"] for t in r[0]["result"]["tools"]}
        self.assertTrue({"pc_run", "pc_read_file", "pc_write_file", "pc_list_dir", "pc_open_app"} <= names)
        self.assertTrue(r[5]["result"]["isError"])  # nothing to open: the tool says so instead of pretending
        self.assertIn("mcp-pc-ok", r[1]["result"]["content"][0]["text"])
        self.assertFalse(r[2]["result"]["isError"])
        self.assertEqual(r[3]["result"]["content"][0]["text"], "привет")
        self.assertIn("pc-note.txt", r[4]["result"]["content"][0]["text"])

    def test_action_tools_over_mcp(self):
        target = self.dir / "mcp-action-note.md"
        r = self.session(
            "claude",
            [
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "read_file", "arguments": {"path": str(self.dir / "70 Memory" / "Profile.md")}},
                },
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "write_file", "arguments": {"path": str(target), "body": "из MCP"}},
                },
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {"name": "list_files", "arguments": {"path": str(self.dir / "70 Memory")}},
                },
            ],
        )
        names = {t["name"] for t in r[0]["result"]["tools"]}
        self.assertTrue({"read_file", "write_file", "list_files", "find_files", "run_command", "open_app"} <= names)
        self.assertIn("Иван", r[1]["result"]["content"][0]["text"])
        self.assertFalse(r[2]["result"]["isError"])
        self.assertEqual(target.read_text(encoding="utf-8").strip(), "из MCP")
        self.assertIn("Profile.md", r[3]["result"]["content"][0]["text"])

    def test_pc_tools_respect_the_switch(self):
        P.save(Vault(self.dir), {"pc_access": False})
        r = self.session(
            "claude",
            [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": "pc_run", "arguments": {"command": "echo nope"}},
                }
            ],
        )
        self.assertTrue(r[0]["result"]["isError"])
        self.assertIn("выключен", r[0]["result"]["content"][0]["text"])

    def test_chatgpt_limits_over_mcp(self):
        lock_cloud(Vault(self.dir))
        r = self.session(
            "chatgpt",
            [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": "memory_remember", "arguments": {"fact": "x", "where": "rules"}},
                },
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "memory_search", "arguments": {"query": "доход"}},
                },
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "memory_stale", "arguments": {}},
                },
            ],
        )
        self.assertTrue(r[0]["result"]["isError"])
        self.assertEqual(r[1]["result"]["content"][0]["text"], "Ничего не нашлось.")
        self.assertNotIn("Доход", r[2]["result"]["content"][0]["text"])

    def test_bad_json_does_not_kill_server(self):
        p = subprocess.run(
            [sys.executable, "-m", "mnema", "--vault", str(self.dir), "mcp"],
            input=b"{not json\n" + json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}).encode() + b"\n",
            capture_output=True,
            env=ENV,
            cwd=str(REPO),
            timeout=60,
        )
        lines = [json.loads(l) for l in p.stdout.decode().splitlines()]
        self.assertEqual(lines[0]["error"]["code"], -32700)
        self.assertEqual(lines[1]["result"], {})


class TestCli(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_init_interview_context(self):
        v = self.dir / "vault"
        self.assertEqual(run_cli("init", str(v)).returncode, 0)
        answers = self.dir / "a.json"
        answers.write_text(
            json.dumps(
                {
                    "who": "Мария, дизайнер интерфейсов.",
                    "where": "Казань",
                    "focus": "портфолио, переезд",
                    "style": "на ты, коротко",
                    "never": "не хвалить без повода; не писать длинно",
                    "projects": "Портфолио, Курс",
                    "people": "Олег — партнёр по студии; Анна — заказчица",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self.assertEqual(run_cli("interview", "--answers", str(answers), vault=v).returncode, 0)
        self.assertTrue((v / "20 Projects" / "Портфолио" / "_Project.md").exists())
        self.assertIn("партнёр по студии", (v / "30 People" / "Олег.md").read_text(encoding="utf-8"))
        ctx = run_cli("context", "--client", "chatgpt", vault=v).stdout.decode("utf-8")
        self.assertIn("Мария", ctx)
        self.assertIn("Нельзя: не хвалить без повода", ctx)
        self.assertNotIn("Олег", ctx)  # people hidden from chatgpt

    def test_remember_undo_journal(self):
        v = self.dir / "vault"
        run_cli("init", str(v))
        r = run_cli("remember", "Купить домен", "--to", "project:Сайт", vault=v)
        eid = r.stdout.decode().strip().split()[-1]
        self.assertTrue((v / "20 Projects" / "Сайт" / "_Project.md").exists())
        self.assertEqual(run_cli("undo", eid, vault=v).returncode, 0)
        self.assertFalse((v / "20 Projects" / "Сайт" / "_Project.md").exists())
        self.assertIn("откат", run_cli("journal", vault=v).stdout.decode("utf-8"))
        bad = run_cli("remember", "x", "--to", "rules", "--client", "chatgpt", vault=v)
        self.assertNotEqual(bad.returncode, 0)

    def test_hook_parts_fit_claude_limit(self):
        v = Vault(self.dir / "vault")
        init_vault(v)
        fill(v)
        for i in range(80):
            remember(v, f"решение {i} " + "подробности " * 40, "decisions")
        parts, i = [], 0
        while True:
            res = json.loads(run_cli("hook", "--part", str(i), vault=v.root).stdout.decode("utf-8"))
            if not res:
                break
            parts.append(res["hookSpecificOutput"]["additionalContext"])
            i += 1
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(len(p) < 10000 for p in parts))  # Claude Code keeps max 10 000 chars per hook

    def test_migrate_old_name(self):
        """Запись прежней Mnema (mnema) в настройках Claude переходит на mnemai, чужие серверы не трогаются."""
        from mnema.cli import migrate_mcp

        cfg = self.dir / "old.json"
        old = {"command": "C:/x/mnema-cli.exe", "args": ["mcp", "--client", "claude"], "env": {}}
        cfg.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}, "mnema": old}}), encoding="utf-8")
        self.assertEqual(migrate_mcp({"claude-desktop": cfg}), ["claude-desktop"])
        data = json.loads(cfg.read_text(encoding="utf-8"))
        self.assertNotIn("mnema", data["mcpServers"])
        self.assertEqual(data["mcpServers"]["mnemai"]["args"], old["args"])
        self.assertIn("other", data["mcpServers"])
        self.assertEqual(migrate_mcp({"claude-desktop": cfg}), [])  # повторно — ничего

    def test_install_desktop(self):
        v = self.dir / "vault"
        run_cli("init", str(v))
        cfg = self.dir / "claude_desktop_config.json"
        cfg.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}}), encoding="utf-8")
        dry = run_cli("install", "claude-desktop", "--config", str(cfg), vault=v)
        self.assertIn("--apply", dry.stdout.decode("utf-8"))
        self.assertNotIn("mnemai", cfg.read_text(encoding="utf-8"))  # dry run changes nothing
        run_cli("install", "claude-desktop", "--config", str(cfg), "--apply", vault=v)
        data = json.loads(cfg.read_text(encoding="utf-8"))
        self.assertIn("other", data["mcpServers"])  # existing servers kept
        self.assertEqual(data["mcpServers"]["mnemai"]["args"][:3], ["-m", "mnema", "mcp"])
        self.assertTrue(cfg.with_suffix(".json.bak").exists())
        # The exact command written into the config must actually start the server.
        srv = data["mcpServers"]["mnemai"]
        p = subprocess.run(
            [srv["command"], *srv["args"]],
            input=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}).encode() + b"\n",
            capture_output=True,
            env={**os.environ, **srv["env"]},
            cwd=str(self.dir),
            timeout=60,
        )
        self.assertEqual(
            json.loads(p.stdout.decode().splitlines()[0])["result"], {}, p.stderr.decode("utf-8", "replace")
        )

    def test_vault_flag_after_command(self):
        v = self.dir / "vault"
        run_cli("init", str(v))
        p = subprocess.run(
            [sys.executable, "-m", "mnema", "context", "--client", "claude", "--vault", str(v)],
            capture_output=True,
            env=ENV,
            cwd=str(REPO),
        )
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))


if __name__ == "__main__":
    unittest.main()
