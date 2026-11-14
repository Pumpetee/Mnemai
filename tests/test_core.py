import os
import datetime as dt
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())  # never touch the real home
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mnema.clients import get_client, load_clients, save_clients  # noqa: E402
from mnema.journal import UndoError, events, undo  # noqa: E402
from mnema.memory import PermissionDenied, context_for, init_vault, remember, split_chunks  # noqa: E402
from mnema.vault import Vault, dump_frontmatter, parse_frontmatter  # noqa: E402
from hidden_topics import lock_cloud  # noqa: E402

TODAY = dt.date(2026, 10, 18)


def fill(v: Vault):
    v.write_raw(
        "70 Memory/Profile.md",
        """---
updated: 2026-10-01
---

# Обо мне

Иван, предприниматель из Екатеринбурга, строю свой продукт.

## Как со мной говорить

- Коротко, без воды.

## Деньги #money

Доход 100к в месяц (статус 01.08.2026).

### Кредитка

Последний рубеж.
""",
    )
    v.write_raw(
        "20 Projects/Сайт/_Project.md",
        """---
status: active
goal: показать макет заказчику
updated: 2026-10-10
---

# Сайт

Макет готов.
""",
    )
    v.write_raw(
        "20 Projects/Старый/_Project.md",
        """---
status: active
goal: что-то давнее
updated: 2026-07-01
---

# Старый

Давно не трогали.
""",
    )
    v.write_raw("20 Projects/Архив/_Project.md", "---\nstatus: archive\n---\n\n# Архив\n")
    v.write_raw("30 People/Ким.md", "# Ким\n\nПартнёр по сайту, любит короткие письма.\n")


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.v = Vault(self.dir)
        init_vault(self.v)
        fill(self.v)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class TestVault(Base):
    def test_init(self):
        for f in (
            "70 Memory/Profile.md",
            "70 Memory/Rules.md",
            "00 Inbox/Inbox.md",
            "10 Now.md",
            "70 Memory/Index.md",
            "20 Projects",
            "30 People",
            "60 Events",
            "70 Memory/Cards",
            "70 Memory/Fact archive",
            "80 Meetings",
            "90 System/Journal",
            "95 Saves",
            "99 Archive",
            ".mnema/clients.json",
            ".mnema/token",
        ):
            self.assertTrue((self.dir / f).exists(), f)

    def test_frontmatter_roundtrip(self):
        meta, body = parse_frontmatter(dump_frontmatter({"status": "active", "tags": ["a", "b"]}, "# T\n"))
        self.assertEqual(meta, {"status": "active", "tags": ["a", "b"]})
        self.assertTrue(body.startswith("# T"))

    def test_scopes(self):
        self.assertEqual(self.v.read("70 Memory/Profile.md").scope, "profile")
        self.assertEqual(self.v.read("20 Projects/Сайт/_Project.md").scope, "projects")
        self.assertEqual(self.v.read("30 People/Ким.md").scope, "people")

    def test_tagged_sections_hidden_with_children(self):
        n = self.v.read("70 Memory/Profile.md")
        visible = n.visible_text({"money"})
        self.assertNotIn("100к", visible)
        self.assertNotIn("Последний рубеж", visible)  # nested ### inherits #money
        self.assertIn("Коротко", visible)

    def test_path_escape_blocked(self):
        with self.assertRaises(ValueError):
            self.v.path("../outside.md")

    def test_stale(self):
        stale = self.v.stale(TODAY)
        texts = " | ".join(s.text for s in stale)
        self.assertIn("Доход", texts)  # status date 01.08 > 30 days
        self.assertIn("Старый", texts)  # project updated 01.07
        self.assertNotIn("Сайт", texts)

    def test_search(self):
        hits = self.v.search("короткие письма")
        self.assertTrue(any("Ким" in rel for rel, _ in hits))
        hits = self.v.search("доход", deny_tags={"money"})
        self.assertFalse(hits)


class TestContext(Base):
    def test_chatgpt_sees_projects_not_money_or_people(self):
        lock_cloud(self.v)
        text, parts = context_for(self.v, "chatgpt", today=TODAY)
        self.assertIn("Сайт", text)
        self.assertNotIn("100к", text)
        self.assertNotIn("Последний рубеж", text)
        self.assertNotIn("Партнёр по сайту", text)  # people not allowed for chatgpt
        self.assertNotIn("Архив", text)  # archived project excluded
        self.assertEqual(parts, 1)

    def test_gemini_now_layer_has_no_projects(self):
        lock_cloud(self.v)
        text, _ = context_for(self.v, "gemini", today=TODAY)
        self.assertIn("Иван", text)
        self.assertNotIn("показать макет", text)
        self.assertNotIn("Сайт", text)
        self.assertNotIn("Доход", text)  # stale money fact must not leak via "Проверить"

    def test_claude_sees_everything(self):
        text, _ = context_for(self.v, "claude", today=TODAY)
        for s in ("100к", "Партнёр по сайту", "Сайт"):
            self.assertIn(s, text)

    def test_unknown_client_minimal(self):
        c = get_client(self.v, "some-app")
        self.assertEqual(set(c.scopes), {"profile", "rules"})
        self.assertFalse(c.can_write)

    def test_disabled_client_gets_nothing(self):
        cl = load_clients(self.v)
        cl["chatgpt"].enabled = False
        save_clients(self.v, cl)
        text, parts = context_for(self.v, "chatgpt", today=TODAY)
        self.assertEqual((text, parts), ("", 0))

    def test_read_is_journaled(self):
        lock_cloud(self.v)
        context_for(self.v, "chatgpt", today=TODAY)
        ev = events(self.v)[0]
        self.assertEqual((ev["client"], ev["action"]), ("chatgpt", "read"))
        self.assertIn("скрыто: деньги", ev["summary"])

    def test_chunks(self):
        text = ("строка " * 30 + "\n") * 400
        chunks = split_chunks(text, 9000)
        self.assertTrue(all(len(c) <= 9000 for c in chunks))
        self.assertEqual("".join(chunks), text)
        self.assertEqual(split_chunks("x" * 20000, 9000)[0], "x" * 9000)

    def test_parts(self):
        for i in range(60):
            remember(self.v, f"важный факт номер {i} " + "подробности " * 30, "decisions", today=TODAY)
        whole, n = context_for(self.v, "claude", today=TODAY)
        self.assertGreater(n, 1)
        p0, _ = context_for(self.v, "claude", part=0, today=TODAY)
        self.assertTrue(p0.startswith("[Память владельца, часть 1 из"))
        empty, _ = context_for(self.v, "claude", part=n, today=TODAY)
        self.assertEqual(empty, "")


class TestRemember(Base):
    def test_inbox_and_journal(self):
        ev = remember(self.v, "Встреча с Ким в понедельник", client_id="chatgpt", today=TODAY)
        self.assertIn("18.10.2026 · Встреча с Ким в понедельник · ChatGPT", self.v.read_raw("00 Inbox/Inbox.md"))
        self.assertEqual(events(self.v)[0]["id"], ev["id"])

    def test_decisions_newest_first(self):
        remember(self.v, "первое", "decisions", today=TODAY)
        remember(self.v, "второе", "decisions", today=TODAY)
        body = self.v.read_raw("60 Events/2026-10.md")
        self.assertLess(body.index("второе"), body.index("первое"))

    def test_events_ordered_by_said_date(self):
        remember(self.v, "первое", "decisions", today=TODAY)
        remember(self.v, "второе", "decisions", today=TODAY - dt.timedelta(days=5))
        body = self.v.read_raw("60 Events/2026-10.md")
        self.assertLess(body.index("первое"), body.index("второе"))

    def test_unknown_status_word_goes_to_frontmatter(self):
        remember(self.v, "Статус: приостановлено", "project:Бот", today=TODAY)
        n = self.v.read("20 Projects/Бот/_Project.md")
        self.assertEqual(n.meta["status"], "приостановлено")
        self.assertNotIn("Статус: приостановлено", n.body)

    def test_project_existing_and_new(self):
        remember(self.v, "показал заказчику", "project:Сайт", today=TODAY)
        n = self.v.read("20 Projects/Сайт/_Project.md")
        self.assertIn("## Журнал", n.body)
        self.assertEqual(n.meta["updated"], "2026-10-18")
        remember(self.v, "старт", "project:Новый продукт", today=TODAY)
        self.assertTrue((self.dir / "20 Projects" / "Новый продукт" / "_Project.md").exists())
        self.assertIn("новый проект «Новый продукт»", self.v.read_raw("60 Events/2026-10.md"))

    def test_person(self):
        remember(self.v, "переехал в Москву", "person:Ким", today=TODAY)
        self.assertIn("переехал в Москву", self.v.read_raw("30 People/Ким.md"))

    def test_permissions(self):
        with self.assertRaises(PermissionDenied):
            remember(self.v, "x", "decisions", client_id="cursor")  # cursor is read-only
        with self.assertRaises(PermissionDenied):
            remember(self.v, "x", "person:Ким", client_id="chatgpt")  # people not allowed
        with self.assertRaises(PermissionDenied):
            remember(self.v, "x", "decisions", client_id="unknown-app")
        with self.assertRaises(PermissionDenied):
            remember(self.v, "x", "rules", client_id="chatgpt")  # outside AI can't rewrite rules
        remember(self.v, "x", "decisions", client_id="claude")  # claude may

    def test_undo(self):
        before = self.v.read_raw("00 Inbox/Inbox.md")
        ev = remember(self.v, "ошибка", today=TODAY)
        undo(self.v, ev["id"])
        self.assertEqual(self.v.read_raw("00 Inbox/Inbox.md"), before)
        with self.assertRaises(UndoError):
            undo(self.v, ev["id"])  # already undone

    def test_undo_new_file_deletes_it(self):
        ev = remember(self.v, "старт", "project:Временный", today=TODAY)
        undo(self.v, ev["id"])
        self.assertFalse((self.dir / "20 Projects" / "Временный" / "_Project.md").exists())

    def test_undo_conflict(self):
        # a later edit elsewhere in the file: only this write's line goes, the edit stays
        ev = remember(self.v, "факт", today=TODAY)
        self.v.write_raw("00 Inbox/Inbox.md", self.v.read_raw("00 Inbox/Inbox.md") + "- правка руками\n")
        undo(self.v, ev["id"])
        inbox = self.v.read_raw("00 Inbox/Inbox.md")
        self.assertNotIn("· факт", inbox)
        self.assertIn("- правка руками", inbox)
        # the written line itself was changed by hand: no safe way back
        ev = remember(self.v, "второй факт", today=TODAY)
        self.v.write_raw("00 Inbox/Inbox.md", self.v.read_raw("00 Inbox/Inbox.md").replace("второй факт", "исправлено"))
        with self.assertRaises(UndoError):
            undo(self.v, ev["id"])


if __name__ == "__main__":
    unittest.main()
