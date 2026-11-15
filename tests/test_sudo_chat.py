"""The administrator password for sudo is asked in the chat: one field, one entry, and never a terminal window."""

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
os.environ["MNEMA_NO_KEYRING"] = "1"  # a test password never goes to the real system keychain

from mnema.agent import profile as P  # noqa: E402
from mnema.chat import engine as CH, providers as PR, tools as TL  # noqa: E402
from mnema.journal import events  # noqa: E402
from mnema.memory import init_vault  # noqa: E402
from mnema.vault import Vault  # noqa: E402


def _vault() -> Vault:
    v = Vault(Path(tempfile.mkdtemp()))
    init_vault(v)
    PR.save(v, "openai", models=["m1"], key="sk-test-0000000000000000")
    P.save(v, {"tools_ask": False})
    return v


class Script:
    """A fake model: each call answers with the next reply; records what it was sent."""

    def __init__(self, *replies):
        self.replies, self.seen = list(replies), []

    def __call__(self, vault, pid, model, system, messages, stop=None, usage=None, meta=None, **kw):
        self.seen.append((system, [dict(m) for m in messages]))
        yield self.replies.pop(0) if self.replies else "Готово."


class SudoOwner:
    """Types the administrator password in the chat card, like the owner does (or cancels)."""

    def __init__(self, passwords, choice: str = "ok"):
        self.passwords, self.choice = list(passwords), choice
        self.asked: list[tuple[str, bool]] = []
        self.answered = 0
        self.stop = threading.Event()
        threading.Thread(target=self.loop, daemon=True).start()

    def loop(self):
        end = time.time() + 20
        while not self.stop.is_set() and time.time() < end:
            for cid, g in list(CH._gen.items()):
                card = g.get("sudo")
                if not card:
                    continue
                self.asked.append((card["command"], bool(card.get("wrong"))))
                pw = self.passwords.pop(0) if self.passwords else ""
                self.answered += 1
                CH.answer_sudo(cid, card["id"], pw, self.choice)
            if self.answered and not self.passwords:
                return
            time.sleep(0.05)


@unittest.skipIf(os.name == "nt", "the administrator password card is POSIX-only; the fake sudo is a shell script")
class Sudo(unittest.TestCase):
    def setUp(self):
        self.old_stream, self.old_terminal = PR.stream, TL._run_in_terminal
        self.work = Path(tempfile.mkdtemp())
        self.bindir = self.work / "bin"
        self.bindir.mkdir()
        self.marker = self.work / "sudo-env.txt"
        self.fake_sudo()
        self.old_path = os.environ["PATH"]
        os.environ["PATH"] = str(self.bindir) + os.pathsep + self.old_path
        os.environ["MNEMA_SUDO_PW"] = "secret-123"
        os.environ["MNEMA_SUDO_MARK"] = str(self.marker)
        TL._run_in_terminal = lambda *a, **k: (_ for _ in ()).throw(AssertionError("no terminal for sudo"))
        CH._answers.clear()
        TL._sudo_memory.clear()
        self.owners: list[SudoOwner] = []

    def tearDown(self):
        for o in self.owners:
            o.stop.set()
        PR.stream = self.old_stream
        TL._run_in_terminal = self.old_terminal
        os.environ["PATH"] = self.old_path
        for k in ("MNEMA_SUDO_PW", "MNEMA_SUDO_MARK"):
            os.environ.pop(k, None)
        CH._answers.clear()
        TL._sudo_memory.clear()

    def fake_sudo(self):
        fake = self.bindir / "sudo"
        fake.write_text(
            "#!/bin/sh\n"
            'if [ "$1" = "-n" ]; then\n'  # «can sudo work here»: a password is required, not a blocked container
            "  echo 'sudo: a password is required' >&2\n"
            "  exit 1\n"
            "fi\n"
            'if [ "$1" = "-S" ]; then\n'  # the password check: sudo -S -k -v
            "  read -r pw\n"
            '  [ "$pw" = "$MNEMA_SUDO_PW" ] && exit 0\n'
            "  echo 'Sorry, try again.'\n"
            "  exit 1\n"
            "fi\n"
            'printf "%s|%s" "$SUDO_ASKPASS" "$SUDO_ASKPASS_REQUIRE" > "$MNEMA_SUDO_MARK"\n'
            'echo "fake-sudo-ok"\n',
            encoding="utf-8",
        )
        fake.chmod(0o755)

    def owner(self, passwords, choice: str = "ok") -> "SudoOwner":
        o = SudoOwner(passwords, choice)
        self.owners.append(o)
        return o

    def sudo_command(self, tail: str) -> str:
        """The command with the fake `sudo` put back on PATH: a login shell on macOS rebuilds PATH (path_helper)."""
        return f"PATH='{self.bindir}':$PATH sudo {tail}"

    def _send(self, v, text, script, owner):
        PR.stream = script
        r = CH.send(v, text, model="openai:m1", learn=False, sync=True)
        return r, owner

    def test_password_is_asked_in_the_chat_and_the_command_runs_without_a_terminal(self):
        v = _vault()
        command = self.sudo_command("echo mnema-sudo-ok")
        script = Script(f'```mnema run_command command="{command}"\n```', "Готово, поставила.")
        owner = self.owner(["secret-123"])
        r, _ = self._send(v, "Проверь сеть", script, owner)  # not an install: the model asks for the command
        self.assertIn("sudo echo mnema-sudo-ok", owner.asked[0][0])
        self.assertEqual(owner.asked[0][1], False)  # the first card is not the «wrong password» one
        self.assertTrue(self.marker.exists(), "the command must run with the password, not wait for a prompt")
        self.assertIn("force", self.marker.read_text(encoding="utf-8"))
        self.assertIn("[Результат действия от Mnemai]", script.seen[1][1][-1]["text"])
        msgs = CH.load_chat(v, r["chat"])["messages"]
        action = next(m for m in msgs if m.get("kind") == "action")
        self.assertFalse(action.get("pending"))
        blob = "".join(str(m.get("text") or "") for m in msgs)
        self.assertNotIn("secret-123", blob, "the password must never enter the conversation")
        self.assertNotIn("secret-123", "".join(e["summary"] for e in events(v, 50)))
        self.assertNotIn("secret-123", str(script.seen[-1]), "the model must never see the password")
        self.assertEqual(TL.sudo_cached(v), "secret-123")  # remembered for the next sudo, not asked again

    def test_a_wrong_password_is_asked_again_and_nothing_runs_with_it(self):
        v = _vault()
        command = self.sudo_command("echo second-try")
        script = Script(f'```mnema run_command command="{command}"\n```', "Готово.")
        owner = self.owner(["not-it", "secret-123"])
        self._send(v, "Поставь пакет", script, owner)
        self.assertEqual([wrong for _, wrong in owner.asked], [False, True])
        self.assertIn("force", self.marker.read_text(encoding="utf-8"))
        self.assertEqual(TL.sudo_cached(v), "secret-123")

    def test_cancel_means_the_command_is_not_run_and_the_model_is_told(self):
        v = _vault()
        command = self.sudo_command("echo never")
        script = Script(f'```mnema run_command command="{command}"\n```', "Хорошо, не выполняю.")
        owner = self.owner([], choice="no")
        r, _ = self._send(v, "Поставь пакет", script, owner)
        self.assertEqual(len(owner.asked), 1)
        self.assertFalse(self.marker.exists())
        self.assertIn("не ввёл пароль", script.seen[1][1][-1]["text"])
        msgs = CH.load_chat(v, r["chat"])["messages"]
        self.assertTrue(any("Не выполнено: нужен пароль администратора" in (m.get("text") or "") for m in msgs))

    def test_the_password_is_typed_once_even_with_two_sudo_commands(self):
        v = _vault()
        script = Script(
            f'```mnema run_command command="{self.sudo_command("echo first")}"\n```',
            f'```mnema run_command command="{self.sudo_command("echo second")}"\n```',
            "Оба готовы.",
        )
        owner = self.owner(["secret-123"])
        self._send(v, "Две команды с sudo", script, owner)
        self.assertEqual(len(owner.asked), 1, "the second sudo must reuse the password from the chat")

    def test_commands_run_hidden_unless_a_terminal_is_asked(self):
        v = _vault()
        script = Script('```mnema run_command command="echo hidden-ok"\n```', "Готово.")
        self._send(v, "Проверь систему", script, self.owner([]))
        self.assertIn("hidden-ok", script.seen[1][1][-1]["text"])

    def test_needs_sudo_only_for_the_command_itself(self):
        self.assertTrue(TL.needs_sudo("sudo dnf install -y nmap"))
        self.assertTrue(TL.needs_sudo("echo ok && sudo true"))
        self.assertFalse(TL.needs_sudo("echo sudoku"))
        self.assertFalse(TL.needs_sudo("ls /usr/sbin"))
        self.assertFalse(TL.needs_sudo(""))

    def test_the_install_shortcut_asks_the_password_and_never_the_model(self):
        v = _vault()
        owner = self.owner(["secret-123"])
        calls: list[int] = []

        def fake_script(*a, **k):
            calls.append(1)
            raise AssertionError("the model must not be called for an install")

        PR.stream = fake_script
        with (
            patch.object(TL, "package_manager", lambda: "dnf"),
            patch.object(TL, "resolve_package", lambda pm, term: "nmap"),
            patch.object(TL, "install_command", lambda pm, names: self.sudo_command("echo mnema-install-ok")),
        ):
            r = CH.send(v, "установи nmap", model="openai:m1", learn=False, sync=True)
        self.assertEqual(calls, [])
        self.assertTrue(self.marker.exists(), "the install must run with the password from the chat card")
        self.assertEqual(owner.asked[0][1], False)
        msgs = CH.load_chat(v, r["chat"])["messages"]
        self.assertTrue(any("поставила nmap" in (m.get("text") or "") for m in msgs))
        self.assertTrue(any("mnema-install-ok" in (m.get("detail") or "") for m in msgs))

    def test_a_container_without_privileges_is_explained_without_a_password_card(self):
        v = _vault()
        script = Script(f'```mnema run_command command="{self.sudo_command("echo never")}"\n```', "Готово.")
        with patch.object(TL, "sudo_blocked", lambda: "контейнер без новых привилегий"):
            r, _ = self._send(v, "Проверь сеть", script, self.owner([]))
        msgs = CH.load_chat(v, r["chat"])["messages"]
        self.assertTrue(any("недоступен" in (m.get("text") or "") for m in msgs))
        self.assertFalse(self.marker.exists(), "the command must not run in a blocked environment")


if __name__ == "__main__":
    unittest.main()
