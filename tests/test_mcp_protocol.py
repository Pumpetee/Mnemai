"""The MCP server's protocol behaviour: parallel requests, cancellation, progress, honest errors, safe tools."""

import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())
os.environ["MNEMA_NO_KEYRING"] = "1"

from mnema.agent import profile as P  # noqa: E402
from mnema.mcp_server import TOOLS, Server  # noqa: E402
from mnema.memory import init_vault  # noqa: E402
from mnema.vault import Vault  # noqa: E402


def _vault() -> Vault:
    v = Vault(Path(tempfile.mkdtemp()))
    init_vault(v)
    return v


def _req(mid, method, params=None):
    msg = {"jsonrpc": "2.0", "id": mid, "method": method}
    if params is not None:
        msg["params"] = params
    return msg


class Protocol(unittest.TestCase):
    def setUp(self):
        self.v = _vault()
        self.srv = Server(self.v, "claude")

    def test_initialize_and_capabilities(self):
        r = self.srv.handle(_req(1, "initialize", {"protocolVersion": "2025-06-18"}))
        res = r["result"]
        self.assertEqual(res["protocolVersion"], "2025-06-18")
        self.assertIn("tools", res["capabilities"])
        self.assertIn("resources", res["capabilities"])
        self.assertIn("prompts", res["capabilities"])
        self.assertIn("logging", res["capabilities"])
        self.assertIn("память", res["instructions"].lower())

    def test_every_tool_has_a_title_and_annotations(self):
        tools = self.srv.handle(_req(2, "tools/list"))["result"]["tools"]
        self.assertEqual(len(tools), len(TOOLS))
        for t in tools:
            self.assertIsInstance(t.get("title"), str, t["name"])
            ann = t.get("annotations") or {}
            for key in ("readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint"):
                self.assertIsInstance(ann.get(key), bool, (t["name"], key))
        by = {t["name"]: t for t in tools}
        self.assertTrue(by["memory_search"]["annotations"]["readOnlyHint"])
        self.assertTrue(by["pc_delete"]["annotations"]["destructiveHint"])
        self.assertTrue(by["web_search"]["annotations"]["openWorldHint"])

    def test_pc_run_never_opens_a_terminal_from_mcp(self):
        by = {t["name"]: t for t in TOOLS}
        self.assertNotIn("terminal", by["pc_run"]["inputSchema"]["properties"])
        self.assertNotIn("terminal", by["run_command"]["inputSchema"]["properties"])
        import mnema.chat.tools as TL

        with patch.object(TL, "_run_in_terminal", side_effect=AssertionError("no window from MCP")):
            r = self.srv.handle(
                _req(
                    3,
                    "tools/call",
                    {"name": "run_command", "arguments": {"command": "echo mcp-hidden", "terminal": True}},
                )
            )
        self.assertFalse(r["result"]["isError"])
        self.assertIn("mcp-hidden", r["result"]["content"][0]["text"])

    def test_a_refusal_is_a_tool_error(self):
        P.save(self.v, {"memory_on": False})
        r = self.srv.handle(_req(4, "tools/call", {"name": "memory_context", "arguments": {}}))
        self.assertTrue(r["result"]["isError"])
        self.assertIn("выключена", r["result"]["content"][0]["text"])

    def test_a_broken_tool_is_a_tool_error_not_a_crash(self):
        r = self.srv.handle(_req(5, "tools/call", {"name": "pc_read_file", "arguments": {"path": "/nope/none.txt"}}))
        self.assertTrue(r["result"]["isError"])
        self.assertIn("нет", r["result"]["content"][0]["text"])

    def test_unknown_tool_is_a_protocol_error(self):
        r = self.srv.handle(_req(6, "tools/call", {"name": "nope", "arguments": {}}))
        self.assertEqual(r["error"]["code"], -32602)

    def test_ping_is_answered_while_a_command_runs(self):
        seen = {}

        def long_call():
            t0 = time.time()
            self.srv.handle(_req(7, "tools/call", {"name": "pc_run", "arguments": {"command": "sleep 1.2"}}))
            seen["long"] = time.time() - t0

        th = threading.Thread(target=long_call, daemon=True)
        th.start()
        time.sleep(0.2)
        t0 = time.time()
        r = self.srv.handle(_req(8, "ping"))
        took = time.time() - t0
        self.assertEqual(r["result"], {})
        self.assertLess(took, 0.7, "ping must not wait for the running command")
        th.join(timeout=5)

    def test_progress_notifications_reach_the_client(self):
        notifications = []
        srv = Server(self.v, "claude", writer=notifications.append)
        r = srv.handle(
            _req(
                9,
                "tools/call",
                {
                    "name": "pc_run",
                    "arguments": {"command": "echo one; sleep 0.3; echo two"},
                    "_meta": {"progressToken": "tok-1"},
                },
            )
        )
        self.assertFalse(r["result"]["isError"])
        progress = [n for n in notifications if n.get("method") == "notifications/progress"]
        self.assertTrue(progress, "a long command reports its progress")
        self.assertEqual(progress[0]["params"]["progressToken"], "tok-1")

    def test_cancelled_request_stops_the_command(self):
        srv = Server(self.v, "claude")
        stdin_r, stdin_w = os.pipe()
        stdout_r, stdout_w = os.pipe()
        stdin = os.fdopen(stdin_r, "rb")
        stdout = os.fdopen(stdout_w, "wb")
        thread = threading.Thread(target=srv.serve, args=(stdin, stdout), daemon=True)
        thread.start()
        writer = os.fdopen(stdin_w, "wb")
        reader = os.fdopen(stdout_r, "rb")
        started = time.time()
        try:
            writer.write(
                (
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": 11,
                            "method": "tools/call",
                            "params": {"name": "pc_run", "arguments": {"command": "sleep 5"}},
                        }
                    )
                    + "\n"
                ).encode()
            )
            writer.flush()
            time.sleep(0.4)
            writer.write(
                (
                    json.dumps({"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 11}})
                    + "\n"
                ).encode()
            )
            writer.flush()
            line = reader.readline()
            took = time.time() - started
        finally:
            writer.close()
            reader.close()
            thread.join(timeout=5)
        resp = json.loads(line)
        self.assertEqual(resp["id"], 11)
        self.assertEqual(resp["error"]["code"], -32800)
        self.assertLess(took, 3, "cancelled command must stop at once")

    def test_sudo_is_refused_without_a_password(self):
        import mnema.chat.tools as TL

        with patch.object(TL, "sudo_cached", lambda vault: ""):
            r = self.srv.handle(
                _req(12, "tools/call", {"name": "pc_run", "arguments": {"command": "sudo dnf install -y nmap"}})
            )
        self.assertTrue(r["result"]["isError"])
        self.assertIn("sudo", r["result"]["content"][0]["text"])

    def test_resource_templates_and_pagination(self):
        r = self.srv.handle(_req(13, "resources/templates/list"))
        uris = [t["uriTemplate"] for t in r["result"]["resourceTemplates"]]
        self.assertIn("mnema://memory/{path}", uris)
        many = [{"uri": f"mnema://memory/{i}.md", "name": f"{i}.md"} for i in range(250)]
        with patch.object(self.srv, "_resources", lambda: many):
            first = self.srv.handle(_req(14, "resources/list"))["result"]
            self.assertEqual(len(first["resources"]), 200)
            self.assertIn("nextCursor", first)
            second = self.srv.handle(_req(15, "resources/list", {"cursor": first["nextCursor"]}))["result"]
            self.assertEqual(len(second["resources"]), 50)
            self.assertNotIn("nextCursor", second)


if __name__ == "__main__":
    unittest.main()
