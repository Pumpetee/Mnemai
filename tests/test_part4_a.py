"""Часть 4, область A: решения владельца по памяти, шифрованию, журналу и настройкам безопасности.

Решения (20.11.2026):
1. Ротация журнала: порог 10 МБ, хранится 5 архивов (journal.rotate).
2. Recovery-ключ шифрования: генерируется и показывается один раз при включении пароля; забытый пароль
   восстанавливается только по нему (crypt.enable / crypt.recover).
3. Предупреждение о бинарниках — текст в интерфейсе (здесь проверяется только контракт статуса).
4. Экспорт памяти запрещён при включённом шифровании (POST /api/memory/export → 403).
5. Восстановление из снапшота дня («95 Saves») — GET /api/saves, POST /api/saves/restore.
6. Вложения удалённого чата остаются в Saves (move_chat_files_to_saves + POST /api/chat/delete).
7. VPN: неверный ключ — ошибка с предложением ввести ключ вручную; автодетект отдаёт списки.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())
os.environ["MNEMA_NO_KEYRING"] = "1"

from mnema import crypt, journal  # noqa: E402
from mnema.http_router import dispatch  # noqa: E402
from mnema.memory import init_vault, list_saves, move_chat_files_to_saves  # noqa: E402
from mnema.vault import Vault  # noqa: E402

PW = "правильный пароль 42"


def _vault() -> Vault:
    v = Vault(Path(tempfile.mkdtemp()))
    init_vault(v)
    return v


def forget_keys():
    crypt._keys.clear()
    crypt._tried.clear()


class RotateJournal(unittest.TestCase):
    """Решение 1: журнал ротируется при пороге, архивы с датой, хранится ровно 5."""

    def test_rotate_threshold_and_keep(self):
        v = _vault()
        f = v.service / "journal.jsonl"
        f.write_text("x" * 2000, encoding="utf-8")  # over 1 KB: rotate with mb=0.001
        r = journal.rotate(v, mb=0.001, keep=5)
        self.assertIsNotNone(r)
        self.assertFalse(f.exists())  # the journal itself moved into the archive
        self.assertTrue(r["archived"].startswith("journal-"))
        self.assertTrue((v.service / r["archived"]).exists())

    def test_rotate_keeps_five_archives(self):
        v = _vault()
        for i in range(7):
            f = v.service / "journal.jsonl"
            f.write_text("x" * 2000, encoding="utf-8")
            journal.rotate(v, mb=0.001, keep=5)
        olds = sorted(v.service.glob("journal-*.jsonl"))
        self.assertEqual(len(olds), 5)

    def test_rotate_below_threshold_noop(self):
        v = _vault()
        f = v.service / "journal.jsonl"
        f.write_text("мало", encoding="utf-8")
        self.assertIsNone(journal.rotate(v, mb=10, keep=5))
        self.assertTrue(f.exists())


class RecoveryKey(unittest.TestCase):
    """Решение 2: recovery-ключ показывается при включении, восстановление — только по нему."""

    def setUp(self):
        crypt.SCRYPT = {"n": 2**12, "r": 8, "p": 1}
        os.environ["MNEMA_HOME"] = tempfile.mkdtemp()
        self.v = _vault()

    def tearDown(self):
        forget_keys()

    def test_enable_returns_recovery_once(self):
        r = crypt.enable(self.v.root, PW, remember=False)
        self.assertIn("recovery", r)
        self.assertGreaterEqual(len(r["recovery"]), 19)  # XXXX-XXXX-XXXX-XXXX
        cfg = crypt.config(self.v.root)
        self.assertIn("recovery", cfg)
        self.assertNotIn(r["recovery"], json.dumps(cfg))  # the key itself is not stored in the file

    def test_recover_with_recovery_key(self):
        r = crypt.enable(self.v.root, PW, remember=False)
        forget_keys()  # «Mnemai started again»: the password is forgotten, the key is gone
        self.assertFalse(crypt.is_open(self.v.root))
        crypt.recover(self.v.root, r["recovery"], "новый пароль 43")
        forget_keys()
        crypt.unlock(self.v.root, "новый пароль 43", False)  # the new password opens
        with self.assertRaises(crypt.BadPassword):
            forget_keys()
            crypt.unlock(self.v.root, PW, False)  # the old one does not

    def test_recover_bad_key(self):
        crypt.enable(self.v.root, PW, remember=False)
        forget_keys()
        with self.assertRaises(crypt.BadPassword):
            crypt.recover(self.v.root, "WRONG-AAAA-BBBB-CCCC", "новый пароль 43")


class MemoryExport(unittest.TestCase):
    """Решение 4: экспорт памяти открытыми Markdown-файлами; при шифровании — 403 с понятным текстом."""

    def setUp(self):
        crypt.SCRYPT = {"n": 2**12, "r": 8, "p": 1}
        os.environ["MNEMA_HOME"] = tempfile.mkdtemp()
        self.v = _vault()
        (self.v.root / "00 Inbox").mkdir(exist_ok=True)
        (self.v.root / "00 Inbox" / "заметка.md").write_text("факт", encoding="utf-8")

    def tearDown(self):
        forget_keys()

    def test_export_plain(self):
        dest = Path(tempfile.mkdtemp())
        code, body = dispatch(self.v, "POST", "/api/memory/export", {}, {"path": str(dest)})
        self.assertEqual(code, 200)
        self.assertTrue(body["files"] >= 1)
        self.assertTrue((dest / "00 Inbox" / "заметка.md").exists())
        self.assertFalse((dest / "70 Memory" / "Index.md").exists())  # generated files are not exported
        self.assertFalse((dest / "95 Saves").exists())

    def test_export_forbidden_when_encrypted(self):
        crypt.enable(self.v.root, PW, remember=False)
        dest = Path(tempfile.mkdtemp())
        code, body = dispatch(self.v, "POST", "/api/memory/export", {}, {"path": str(dest)})
        self.assertEqual(code, 403)
        self.assertIn("зашифрована", body["error"])

    def test_export_without_path(self):
        code, body = dispatch(self.v, "POST", "/api/memory/export", {}, {"path": ""})
        self.assertEqual(code, 400)


class RestoreFromSave(unittest.TestCase):
    """Решение 5: снапшот дня из «95 Saves» восстанавливает заметку; список отдаётся маршрутом."""

    def test_save_listed_and_restored(self):
        v = _vault()
        rel = "00 Inbox/план.md"
        (v.root / "00 Inbox").mkdir(exist_ok=True)
        (v.root / rel).write_text("утренняя версия", encoding="utf-8")
        from mnema.journal import write_with_journal

        write_with_journal(v, "owner", rel, "вечерняя правка", "правка в тесте")  # saves the morning version
        saves = list_saves(v)
        self.assertTrue(saves)
        hit = next(s for s in saves if s["name"].startswith("план_"))
        code, body = dispatch(v, "POST", "/api/saves/restore", {}, {"path": hit["path"]})
        self.assertEqual(code, 200)
        self.assertEqual(body["rel"], rel)
        self.assertEqual((v.root / rel).read_text(encoding="utf-8"), "утренняя версия")

    def test_restore_unknown_save(self):
        v = _vault()
        code, body = dispatch(v, "POST", "/api/saves/restore", {}, {"path": "95 Saves/нет_2020-01-01.md"})
        self.assertEqual(code, 400)
        self.assertIn("сейв не найден", body["error"])


class AttachmentsStayInSaves(unittest.TestCase):
    """Решение 6: вложения удалённого чата остаются в «95 Saves»."""

    CID = "a1b2c3d4e5f6"

    def test_delete_chat_moves_files_to_saves(self):
        v = _vault()
        (v.service / "chats" / self.CID / "files").mkdir(parents=True)
        (v.service / "chats" / self.CID / "files" / "scan.pdf").write_bytes(b"%PDF-1.4")
        (v.service / "chats" / f"{self.CID}.json").write_text(
            json.dumps({"messages": []}, ensure_ascii=False), encoding="utf-8"
        )
        code, body = dispatch(v, "POST", "/api/chat/delete", {}, {"id": self.CID})
        self.assertEqual(code, 200)
        moved = list((v.root / "95 Saves" / "attachments" / self.CID).glob("*.pdf"))
        self.assertEqual(len(moved), 1)
        self.assertFalse((v.service / "chats" / self.CID / "files" / "scan.pdf").exists())
        self.assertFalse((v.service / "chats" / f"{self.CID}.json").exists())  # the chat itself is deleted

    def test_no_files_folder(self):
        v = _vault()
        self.assertEqual(move_chat_files_to_saves(v, "ffffffff"), [])


class VpnManualHint(unittest.TestCase):
    """Решение 7: неверный ключ — ошибка с предложением ввести ключ вручную; автодетект отдаёт списки."""

    def test_bad_key_suggests_manual_entry(self):
        from mnema import vpnkey

        with mock.patch("mnema.vpnkey.parse", side_effect=ValueError("ключ не понятен")):
            with self.assertRaises(ValueError) as cm:
                vpnkey.connect(mock.Mock(), "мусор")
        self.assertIn("вручную", str(cm.exception))

    def test_detect_shape(self):
        from mnema import vpn_detect

        d = vpn_detect.detect()
        self.assertIsInstance(d.get("proxies"), list)
        self.assertIsInstance(d.get("tunnels"), list)


if __name__ == "__main__":
    unittest.main()
