"""Безопасность хранилища: токен локального API должен быть доступен только владельцу.

На POSIX файл токена создаётся с правами 0600, папка служебных файлов — 0700; файл/папка от старых
версий с широкими правами подтягиваются при следующем обращении. На Windows эти проверки не действуют
(прав семантики нет — проверки пропускаются).
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())  # never touch the real home
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mnema.memory import init_vault, token  # noqa: E402
from mnema.vault import Vault  # noqa: E402


@unittest.skipIf(os.name == "nt", "POSIX-права на Windows не действуют")
class TestTokenPrivacy(unittest.TestCase):
    def test_token_file_is_owner_only_after_init(self):
        d = Path(tempfile.mkdtemp())
        v = Vault(d)
        init_vault(v)
        tok = token(v)
        self.assertTrue(tok)
        self.assertEqual((v.service / "token").stat().st_mode & 0o777, 0o600)
        self.assertEqual(v.service.stat().st_mode & 0o777, 0o700)

    def test_token_created_lazily_is_owner_only(self):
        d = Path(tempfile.mkdtemp())
        v = Vault(d)  # без init_vault: токен создаётся при первом запросе
        tok = token(v)
        self.assertTrue(tok)
        self.assertEqual((v.service / "token").stat().st_mode & 0o777, 0o600)

    def test_world_readable_token_from_old_version_is_healed(self):
        d = Path(tempfile.mkdtemp())
        v = Vault(d)
        init_vault(v)
        f = v.service / "token"
        f.chmod(0o644)  # как оставила старая версия при свободном umask
        self.assertEqual(f.stat().st_mode & 0o777, 0o644)
        token(v)
        self.assertEqual(f.stat().st_mode & 0o777, 0o600)

    def test_token_stable_across_reads(self):
        d = Path(tempfile.mkdtemp())
        v = Vault(d)
        first = token(v)
        self.assertEqual(token(v), first)
        self.assertEqual((v.service / "token").read_text(encoding="utf-8").strip(), first)


if __name__ == "__main__":
    unittest.main()
