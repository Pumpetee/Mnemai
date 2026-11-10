"""Secrets never leave the computer; every cloud request is logged. Fake data only."""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mnema import outgoing as OG  # noqa: E402
from mnema.agent import profile as P  # noqa: E402
from mnema.chat import providers as PR  # noqa: E402
from mnema.memory import init_vault  # noqa: E402
from mnema.vault import Vault  # noqa: E402

TEXT = (
    "Позвони Олегу +7 (999) 123-45-67, карта 4111 1111 1111 1111, пароль: qwerty123, ключ sk-ant-abcdefghijklmnop1234, "
    "паспорт 4510 123456, СНИЛС 112-233-445 95. Бюджет 200 000 ₽, встреча 20.10.2026, номер заказа 1234 5678 9012 3456."
)


class TestRedactor(unittest.TestCase):
    def test_secrets_become_labels_and_come_back(self):
        r = OG.Redactor()
        out = r.apply(TEXT)
        for secret in (
            "999) 123-45-67",
            "4111 1111 1111 1111",
            "qwerty123",
            "sk-ant-abcdefghijklmnop1234",
            "4510 123456",
            "112-233-445 95",
        ):
            self.assertNotIn(secret, out)
        for label in ("[ТЕЛЕФОН-1]", "[КАРТА-1]", "[ПАРОЛЬ-1]", "[КЛЮЧ-1]", "[ПАСПОРТ-1]", "[СНИЛС-1]"):
            self.assertIn(label, out)
        self.assertIn("200 000 ₽", out)  # money, dates and a non-card number stay as they are
        self.assertIn("20.10.2026", out)
        self.assertIn("1234 5678 9012 3456", out)  # fails the card checksum
        self.assertEqual(r.restore(out), TEXT)
        self.assertEqual(r.summary(), {"secret": 1, "password": 1, "card": 1, "passport": 1, "snils": 1, "phone": 1})

    def test_same_value_same_label(self):
        r = OG.Redactor()
        out = r.apply("+7 999 123 45 67 и ещё раз +7 999 123 45 67")
        self.assertEqual(out.count("[ТЕЛЕФОН-1]"), 2)

    def test_label_cut_between_pieces(self):
        r = OG.Redactor()
        r.apply("звони +7 999 123 45 67")
        got = "".join(r.restore_stream(["Набери [ТЕЛ", "ЕФОН-", "1] вечером"]))
        self.assertEqual(got, "Набери +7 999 123 45 67 вечером")


class TestCloudRequests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.v = Vault(self.dir)
        init_vault(self.v)
        self.sent = []
        self.orig = PR._stream_raw

        def fake(vault, pid, model, system, messages, stop=None, usage=None, meta=None):
            self.sent.append((system, messages))
            yield from ["Карта [КА", "РТА-1] принята"]

        PR._stream_raw = fake

    def tearDown(self):
        PR._stream_raw = self.orig
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_cloud_gets_labels_owner_gets_values_log_has_no_values(self):
        usage = {}
        out = "".join(
            PR.stream(
                self.v,
                "openai",
                "gpt-4o",
                "память",
                [{"role": "user", "text": "оплати картой 4111 1111 1111 1111"}],
                usage=usage,
                meta={"purpose": "ответ в чате", "chat": "c1", "memory_sent": 100, "memory_full": 900},
            )
        )
        system, msgs = self.sent[0]
        self.assertNotIn("4111", msgs[0]["text"])
        self.assertIn(OG.NOTE, system)
        self.assertEqual(out, "Карта 4111 1111 1111 1111 принята")
        self.assertEqual(usage["redacted"], {"card": 1})
        log = (self.dir / ".mnema" / "outgoing.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("4111", log)
        rep = OG.report(self.v)
        self.assertEqual((rep["requests"], rep["memory_kept"], rep["redacted"]), (1, 800, {"card": 1}))

    def test_switch_off_sends_as_is(self):
        P.save(self.v, {"redact": False})
        "".join(PR.stream(self.v, "openai", "gpt-4o", "s", [{"role": "user", "text": "4111 1111 1111 1111"}]))
        self.assertIn("4111", self.sent[0][1][0]["text"])

    def test_local_model_is_not_a_cloud_request(self):
        "".join(PR.stream(self.v, "local", "gemma-3-4b", "s", [{"role": "user", "text": "4111 1111 1111 1111"}]))
        self.assertIn("4111", self.sent[0][1][0]["text"])  # never leaves the computer anyway
        self.assertFalse((self.dir / ".mnema" / "outgoing.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
