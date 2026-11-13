"""Learning: sources, brains, ledger, policy, the owner's answers. Demo data only (Иван)."""

import datetime as dt
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["MNEMA_HOME"] = tempfile.mkdtemp()  # secrets of tests never touch the real home

from mnema.learn import engine, settings as S  # noqa: E402
from mnema.learn.brains import NoModelBrain, clean, parse_json, sensitive_tags  # noqa: E402
from mnema.learn.ledger import Ledger, combined  # noqa: E402
from mnema.learn.sources import BRAIN_MARK, Episode, read_mail  # noqa: E402
from mnema.memory import context_for, init_vault  # noqa: E402
from mnema.vault import Vault  # noqa: E402
from test_core import fill  # noqa: E402
from hidden_topics import lock_cloud  # noqa: E402


def cc_line(kind, text, i=0):
    if kind == "user":
        return json.dumps(
            {"type": "user", "message": {"role": "user", "content": text}, "timestamp": f"2026-10-1{i}T10:00:00Z"},
            ensure_ascii=False,
        )
    return json.dumps(
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}},
        ensure_ascii=False,
    )


class FakeBrain:
    """Plays an LLM: returns prepared facts for episodes that contain a trigger word."""

    name = "fake"

    def __init__(self, table):
        self.table, self.calls = table, 0

    def extract(self, episodes, known):
        self.calls += 1
        raw = []
        for e in episodes:
            for trigger, facts in self.table.items():
                if trigger in e.text:
                    raw += [{**f, "ref": e.ref} for f in facts]
        return clean(raw, episodes)


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.v = Vault(self.dir / "vault")
        init_vault(self.v)
        fill(self.v)
        self.cc = self.dir / "claude_projects"
        (self.cc / "proj").mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def settings(self, **src_modes):
        s = S.load(self.v)
        s["sources"]["claude_code"]["options"]["path"] = str(self.cc)
        for sid, mode in src_modes.items():
            s["sources"][sid]["enabled"] = mode != "off"
            s["sources"][sid]["mode"] = mode
        S.save(self.v, s)
        return s

    def chat(self, *turns, name="a.jsonl"):
        f = self.cc / "proj" / name
        with f.open("a", encoding="utf-8") as fh:
            for i, (k, t) in enumerate(turns):
                fh.write(cc_line(k, t, i % 9) + "\n")


class TestNoModel(Base):
    def test_explicit_correction_decision_status(self):
        eps = [
            Episode("claude_code", "1", "", "Запомни, что я переехал в Казань."),
            Episode("claude_code", "2", "", "Решил запускать пилот с отделом продаж."),
            Episode("claude_code", "3", "", "Сайт заказчику показан (статус 12.10.2026)."),
            Episode(
                "claude_code",
                "4",
                "",
                "Нет, не так. Никогда не пиши длинные отчёты.",
                prev="Вот подробный отчёт на 3 страницы",
            ),
        ]
        c = NoModelBrain().extract(eps, "")
        kinds = {x["kind"] for x in c}
        self.assertEqual(kinds, {"fact", "decision", "rule"})
        rule = next(x for x in c if x["kind"] == "rule")
        self.assertIn("Никогда не пиши длинные отчёты", rule["text"])
        self.assertTrue(rule["correction"])
        self.assertEqual(rule["where"], "rules")
        self.assertTrue(any("Казань" in x["text"] for x in c))

    def test_no_correction_without_ai_before(self):
        c = NoModelBrain().extract([Episode("notes", "n", "", "Не надо было брать этот заказ.")], "")
        self.assertFalse([x for x in c if x["kind"] == "rule"])

    def test_sensitive_detection(self):
        self.assertEqual(sensitive_tags("доход 300к в месяц"), ["money"])
        self.assertIn("health", sensitive_tags("врач сказал пить таблетки"))

    def test_parse_json_tolerant(self):
        self.assertEqual(parse_json('Вот: {"facts": [{"text": "x"}]} готово'), [{"text": "x"}])
        self.assertEqual(parse_json("ерунда"), [])


class TestSources(Base):
    def test_claude_code_reads_new_lines_once_and_skips_own_and_service(self):
        self.settings(claude_code="mixed")
        self.chat(
            ("user", "Запомни, что я люблю короткие ответы."),
            ("assistant", "Хорошо"),
            ("user", "<command-name>/clear</command-name>"),
            ("user", BRAIN_MARK + " извлеки факты"),
        )
        r1 = engine.run(self.v, brain=NoModelBrain())
        self.assertEqual(r1["episodes"], 1)
        r2 = engine.run(self.v, brain=NoModelBrain())
        self.assertEqual(r2["episodes"], 0)  # cursor: nothing twice
        self.chat(("user", "Запомни: встреча с Ким по средам."))
        self.assertEqual(engine.run(self.v, brain=NoModelBrain())["episodes"], 1)

    def test_brain_folder_transcripts_are_ignored(self):
        self.settings(claude_code="quiet")
        import re

        own = re.sub(r"[^A-Za-z0-9]", "-", str((self.v.service / "learn" / "brain").resolve()))
        (self.cc / own).mkdir()
        (self.cc / own / "x.jsonl").write_text(cc_line("user", "Запомни, что я космонавт.") + "\n", encoding="utf-8")
        engine.run(self.v, brain=NoModelBrain())
        self.assertNotIn("космонавт", self.v.read_raw("00 Inbox/Inbox.md"))

    def test_chatgpt_export_notes_telegram(self):
        s = self.settings(chatgpt_export="quiet", notes="quiet", telegram="quiet")
        exp = self.dir / "gpt"
        exp.mkdir()
        (exp / "conversations.json").write_text(
            json.dumps(
                [
                    {
                        "id": "c1",
                        "title": "план",
                        "update_time": dt.datetime.now().timestamp(),
                        "mapping": {
                            "a": {
                                "message": {
                                    "id": "m1",
                                    "author": {"role": "user"},
                                    "create_time": dt.datetime.now().timestamp(),
                                    "content": {"parts": ["Запомни, что я пишу на Python."]},
                                }
                            }
                        },
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        notes = self.dir / "notes"
        (notes / ".obsidian").mkdir(parents=True)
        (notes / "план.md").write_text("# План\n\nРешил перенести запуск на ноябрь.\n", encoding="utf-8")
        (notes / ".obsidian" / "x.md").write_text("Запомни, что это служебное.\n", encoding="utf-8")
        tg = self.dir / "tg"
        tg.mkdir()
        (tg / "result.json").write_text(
            json.dumps(
                {
                    "personal_information": {"user_id": 7},
                    "chats": {
                        "list": [
                            {
                                "id": 1,
                                "name": "Ким",
                                "messages": [
                                    {
                                        "id": 1,
                                        "type": "message",
                                        "date": dt.datetime.now().isoformat(timespec="seconds"),
                                        "from_id": "user7",
                                        "text": "Запомни, что Ким отвечает за продажи.",
                                    },
                                    {
                                        "id": 2,
                                        "type": "message",
                                        "date": dt.datetime.now().isoformat(timespec="seconds"),
                                        "from_id": "user9",
                                        "text": "Запомни, что я чужой человек.",
                                    },
                                ],
                            }
                        ]
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        s["sources"]["chatgpt_export"]["options"]["path"] = str(exp)
        s["sources"]["notes"]["options"]["path"] = str(notes)
        s["sources"]["telegram"]["options"]["path"] = str(tg)
        S.save(self.v, s)
        r = engine.run(self.v, brain=NoModelBrain())
        self.assertFalse(r["errors"], r["errors"])
        mem = "\n".join(p.read_text(encoding="utf-8") for p in self.v.root.rglob("*.md") if ".mnema" not in p.parts)
        for must in ("на Python", "перенести запуск на ноябрь", "Ким отвечает за продажи"):
            self.assertIn(must, mem)
        for never in ("служебное", "чужой человек"):
            self.assertNotIn(never, mem)
        # notes: only new lines next time
        (notes / "план.md").write_text(
            "# План\n\nРешил перенести запуск на ноябрь.\nРешено: бюджет пилота согласовать с Ким.\n", encoding="utf-8"
        )
        os.utime(notes / "план.md", (dt.datetime.now().timestamp() + 5,) * 2)
        r2 = engine.run(self.v, brain=NoModelBrain())
        self.assertEqual(r2["by_source"]["notes"]["episodes"], 1)

    def test_notes_never_reads_the_memory_itself(self):
        s = self.settings(notes="quiet")
        s["sources"]["notes"]["options"]["path"] = str(self.dir)  # parent of the vault
        S.save(self.v, s)
        self.v.write_raw("30 People/Тест.md", "# Тест\n\nЗапомни, что это внутри памяти.\n")
        engine.run(self.v, brain=NoModelBrain())
        self.assertNotIn("внутри памяти", self.v.read_raw("00 Inbox/Inbox.md"))

    def test_mail_sent_only_own_text(self):
        class FakeImap:
            def login(self, u, p):
                self.ok = (u, p) == ("ivan@x.ru", "pw")

            def list(self):
                return "OK", [b'(\\HasNoChildren \\Sent) "/" "Sent"']

            def select(self, f, readonly=True):
                self.folder = f

            def uid(self, cmd, *a):
                if cmd == "search":
                    return "OK", [b"5 6"]
                raw = (
                    "From: ivan@x.ru\r\nTo: archi@x.ru\r\nSubject: Пилот\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n"
                    "Решил начать пилот в понедельник с тремя менеджерами.\r\n\r\nOn Mon, Archi wrote:\r\n> Запомни, что я чужой\r\n"
                ).encode()
                return "OK", [(b"1", raw)]

            def logout(self):
                pass

        cur = {}
        eps = read_mail(
            self.v, {"host": "h", "user": "ivan@x.ru", "password": "pw"}, cur, 30, 10, connect=lambda h: FakeImap()
        )
        self.assertEqual(len(eps), 2)
        self.assertIn("пилот в понедельник", eps[0].text)
        self.assertNotIn("чужой", eps[0].text)
        self.assertEqual(cur["uid"], 6)


class TestPolicy(Base):
    TABLE = {
        "кофе": [
            {
                "text": "Пьёт кофе без сахара",
                "kind": "preference",
                "where": "profile:Привычки",
                "key": "кофе",
                "confidence": 0.6,
            }
        ],
        "зарплата": [
            {"text": "Доход 300 тысяч в месяц", "kind": "fact", "where": "inbox", "key": "доход", "confidence": 0.95}
        ],
        "Москва": [
            {
                "text": "Живёт в Москве",
                "kind": "fact",
                "where": "profile:Обо мне",
                "key": "город",
                "confidence": 0.9,
                "contradicts": "Иван, предприниматель из Екатеринбурга, строю свой продукт.",
            }
        ],
        "отчёт": [{"text": "Отвечать без вступлений", "kind": "rule", "confidence": 0.9}],
        "монетизация": [
            {
                "text": "Монетизация Копилки: подписка 199 рублей в месяц",
                "kind": "decision",
                "where": "decisions",
                "key": "монетизация",
                "confidence": 0.95,
            }
        ],
        "уверен": [
            {
                "text": "Главный проект — запуск Mnemai",
                "kind": "fact",
                "where": "inbox",
                "key": "главный проект",
                "confidence": 0.9,
            }
        ],
    }

    def go(self, text, prev="", **modes):
        self.settings(**(modes or {"claude_code": "mixed", "corrections": "mixed"}))
        turns = ([("assistant", prev)] if prev else []) + [("user", text)]
        self.chat(*turns, name=f"{abs(hash(text))}.jsonl")
        return engine.run(self.v, brain=FakeBrain(self.TABLE))

    def test_mixed_confident_goes_in_silently(self):
        r = self.go("я уверен")
        self.assertEqual(r["written"], 1)
        self.assertIn("Главный проект — запуск Mnemai", self.v.read_raw("00 Inbox/Inbox.md"))
        self.assertIn("выучено", self.v.read_raw("00 Inbox/Inbox.md"))

    def test_personal_from_elsewhere_goes_straight_to_a_hidden_section(self):
        lock_cloud(self.v)
        r = self.go("моя зарплата")
        self.assertEqual((r["written"], r["queued"]), (1, 0))
        card = self.v.read_raw("70 Memory/Cards/Деньги.md")
        self.assertIn("Доход 300 тысяч", card)
        self.assertIn("tags: [money]", card)
        text, _ = context_for(self.v, "chatgpt", log=False)
        self.assertNotIn("300 тысяч", text)  # learned money is hidden like the rest
        text, _ = context_for(self.v, "claude", log=False)
        self.assertIn("300 тысяч", text)

    def test_sensitive_fact_in_any_section_is_hidden(self):
        """The brain may pick an ordinary section for a health fact — it must still be hidden."""
        lock_cloud(self.v)
        self.TABLE = {
            **self.TABLE,
            "врач": [
                {
                    "text": "По совету врача работает до 19:00",
                    "kind": "preference",
                    "where": "profile:Режим работы",
                    "confidence": 0.9,
                }
            ],
            "долг": [
                {
                    "text": "Долг по кредиту 300 тысяч, жена не знает",
                    "kind": "fact",
                    "where": "inbox",
                    "confidence": 0.9,
                }
            ],
        }
        self.go("врач сказал", claude_code="quiet")
        self.chat(("user", "про долг"), name="d.jsonl")
        engine.run(self.v, brain=FakeBrain(self.TABLE))
        me = self.v.read_raw("70 Memory/Profile.md")
        self.assertIn("## Режим работы #health", me)
        self.assertIn("tags: [money, private]", self.v.read_raw("70 Memory/Cards/Деньги.md"))
        for client in ("chatgpt", "gemini"):
            text, _ = context_for(self.v, client, log=False)
            self.assertNotIn("врача", text)
            self.assertNotIn("Долг по кредиту", text)

    def test_repetition_raises_confidence_until_it_is_written(self):
        self.assertAlmostEqual(combined([0.6, 0.6]), 0.84)
        self.go("кофе утром")
        it = Ledger(self.v).items[0]
        self.assertEqual(it["state"], "weak")  # not asked about: waits to be seen again
        self.chat(("user", "опять кофе"), name="b.jsonl")
        engine.run(self.v, brain=FakeBrain(self.TABLE))
        it = Ledger(self.v).items[0]
        self.assertEqual((it["count"], it["state"]), (2, "written"))
        self.assertIn("Пьёт кофе без сахара", self.v.read_raw("70 Memory/Profile.md"))

    def test_contradiction_from_elsewhere_is_resolved_by_itself(self):
        r = self.go("переехал в Москва")
        self.assertEqual(r["queued"], 0)
        me = self.v.read_raw("70 Memory/Profile.md")
        self.assertIn("Живёт в Москве", me)
        self.assertIn("строю свой продукт", me)  # without a brain nothing else is lost

    def test_contradiction_with_brain_rewrites_keeping_the_rest(self):
        class Reviser:
            def ask(self, prompt):
                assert "Иван, предприниматель из Екатеринбурга" in prompt
                return "Иван, продакт из Москвы, строю свой продукт."

        orig = engine.make_brain
        engine.make_brain = lambda s: Reviser()
        try:
            self.go("переехал в Москва")
        finally:
            engine.make_brain = orig
        me = self.v.read_raw("70 Memory/Profile.md")
        self.assertIn("Иван, продакт из Москвы, строю свой продукт.", me)
        self.assertNotIn("Екатеринбург", me)

    def ask_in_chat(self, text):
        """A message in a conversation in Mnemai: learning may ask under it."""
        from mnema.chat import engine as CH
        from mnema.learn.sources import Episode

        self.settings(claude_code="mixed", corrections="mixed")
        cid = "abc123abc123"
        CH.save_chat(self.v, {"id": cid, "title": "t", "messages": [{"role": "user", "text": text}], "updated": ""})
        engine.learn_episodes(
            self.v, [Episode("mnema_chat", f"{cid}#1", "", text)], "mnema_chat", brain=FakeBrain(self.TABLE)
        )
        return cid, CH.load_chat(self.v, cid).get("learn_ask")

    def test_in_chat_personal_is_asked_there_once(self):
        cid, q = self.ask_in_chat("моя зарплата и кофе")
        self.assertEqual(q["kind"], "personal")
        self.assertNotIn("300 тысяч", self.v.read_raw("70 Memory/Cards/Деньги.md") or "")
        waiting = Ledger(self.v).queue()  # the question is visible in the queue and in the conversation
        self.assertTrue(any(i["id"] == q["item"] and i["state"] == "asking" for i in waiting))
        engine.review(self.v, q["item"], "keep")
        self.assertIn("Доход 300 тысяч", self.v.read_raw("70 Memory/Cards/Деньги.md"))

    def test_no_second_memory_question_within_cooldown(self):
        """Three facts in a row are not three questions: after one, the next ones are decided silently."""
        from mnema.chat import engine as CH

        cid, q = self.ask_in_chat("моя зарплата")
        self.assertEqual(q["kind"], "personal")
        table = {
            **self.TABLE,
            "врач": [
                {
                    "text": "По совету врача спит восемь часов",
                    "kind": "preference",
                    "where": "profile:Сон",
                    "confidence": 0.9,
                }
            ],
        }
        engine.learn_episodes(
            self.v,
            [Episode("mnema_chat", f"{cid}#2", "", "врач сказал спать восемь часов")],
            "mnema_chat",
            brain=FakeBrain(table),
        )
        self.assertEqual(CH.load_chat(self.v, cid)["learn_ask"]["item"], q["item"])  # the same question stands
        health = [i for i in Ledger(self.v).items if "восемь часов" in i["text"]]
        self.assertEqual(health[0]["state"], "written")  # not asked again: written, undoable in History

    def test_one_answer_takes_all_standing_questions(self):
        from mnema.chat import engine as CH

        cid, q = self.ask_in_chat("моя зарплата")
        self.assertEqual(q["kind"], "personal")
        cid2 = "def456def456"
        CH.save_chat(self.v, {"id": cid2, "title": "t2", "messages": [{"role": "user", "text": "врач"}], "updated": ""})
        table = {
            **self.TABLE,
            "врач": [
                {
                    "text": "По совету врача спит восемь часов",
                    "kind": "preference",
                    "where": "profile:Сон",
                    "confidence": 0.9,
                }
            ],
        }
        engine.learn_episodes(
            self.v, [Episode("mnema_chat", f"{cid2}#1", "", "врач сказал")], "mnema_chat", brain=FakeBrain(table)
        )
        self.assertTrue(CH.load_chat(self.v, cid2).get("learn_ask"))
        self.assertEqual(engine.review_all(self.v, "keep"), 2)  # both standing questions, one answer
        self.assertIn("Доход 300 тысяч", self.v.read_raw("70 Memory/Cards/Деньги.md"))
        self.assertIn("восемь часов", self.v.read_raw("70 Memory/Profile.md"))
        engine.review(self.v, q["item"], "keep")  # an old card answered again must not double the fact
        self.assertEqual(self.v.read_raw("70 Memory/Cards/Деньги.md").count("Доход 300 тысяч"), 1)

    def test_in_chat_contradiction_keep_old(self):
        cid, q = self.ask_in_chat("переехал в Москва")
        self.assertEqual(q["kind"], "conflict")
        self.assertIn("Екатеринбурга", q["old"])
        engine.review(self.v, q["item"], "keep_old")
        self.assertNotIn("Москв", self.v.read_raw("70 Memory/Profile.md"))
        self.assertEqual(Ledger(self.v).get(q["item"])["state"], "rejected")

    def test_explicit_change_replaces_right_away(self):
        base = {
            "text": "Монетизация — разовая покупка 499 рублей",
            "kind": "decision",
            "where": "decisions",
            "confidence": 0.95,
            "count": 1,
            "tags": ["money"],
            "contradicts": "Монетизация — подписка 199 рублей",
            "sources": ["mnema_chat"],
            "last_source": "mnema_chat",
            "evidence": ["Подписку убираем совсем, вместо неё разовая покупка за 499 рублей"],
        }
        settings = S.load(self.v)
        self.assertEqual(engine.decide_why(base, settings, can_ask=True)[0], "replace")
        silent = {**base, "text": "Монетизация 499 рублей", "evidence": ["разовая покупка 499 рублей"]}
        self.assertEqual(engine.decide_why(silent, settings, can_ask=True)[0], "ask")

    def test_explicit_change_replaces_the_old_line_without_a_model_hint(self):
        from mnema.chat import engine as CH
        from mnema.learn.sources import Episode

        self.settings(claude_code="mixed", corrections="mixed")
        cid, q = self.ask_in_chat("моя монетизация: подписка 199 рублей в месяц")
        engine.review(self.v, q["item"], "keep")
        self.assertIn("подписка 199", self.v.read_raw("70 Memory/Cards/Деньги.md"))
        text = "Подписку убираем совсем, вместо неё разовая покупка за 499 рублей"
        CH.save_chat(self.v, {"id": cid, "title": "t", "messages": [{"role": "user", "text": text}], "updated": ""})
        brain = FakeBrain(
            {
                "убираем": [
                    {
                        "text": "Монетизация Копилки: подписка убрана, вместо неё разовая покупка за 499 рублей",
                        "kind": "decision",
                        "where": "decisions",
                        "confidence": 1.0,
                        "evidence": text,
                    }
                ]
            }
        )
        engine.learn_episodes(self.v, [Episode("mnema_chat", f"{cid}#2", "", text)], "mnema_chat", brain=brain)
        card = self.v.read_raw("70 Memory/Cards/Деньги.md")
        self.assertIn("499", card)
        self.assertNotIn("подписка 199", card)
        archived = list((self.v.root / "70 Memory" / "Fact archive").glob("*.md"))
        self.assertTrue(any("199" in f.read_text(encoding="utf-8") for f in archived))

    def test_memory_questions_stay_in_a_queue(self):
        from mnema import api_learn
        from mnema.chat import engine as CH
        from mnema.learn.sources import Episode

        self.settings(claude_code="mixed", corrections="mixed")
        cid = "abc123abc123"
        CH.save_chat(
            self.v, {"id": cid, "title": "t", "messages": [{"role": "user", "text": "моя зарплата"}], "updated": ""}
        )
        brain = FakeBrain(
            {"зарплата": [{"text": "Доход 300 тысяч в месяц", "kind": "fact", "where": "inbox", "confidence": 0.95}]}
        )
        engine.learn_episodes(
            self.v, [Episode("mnema_chat", f"{cid}#1", "", "моя зарплата")], "mnema_chat", brain=brain
        )
        brain2 = FakeBrain(
            {"кредит": [{"text": "Кредит 500 тысяч", "kind": "fact", "where": "inbox", "confidence": 0.95}]}
        )
        engine.learn_episodes(self.v, [Episode("mnema_chat", f"{cid}#2", "", "мой кредит")], "mnema_chat", brain=brain2)
        c = CH.load_chat(self.v, cid)
        self.assertEqual(len(c.get("learn_asks") or []), 2)  # the second question is not lost
        first = c["learn_asks"][0]["item"]
        api_learn.post(self.v, "/api/learn/review", {"chat": cid, "id": first, "action": "keep"})
        c = CH.load_chat(self.v, cid)
        self.assertEqual(len(c.get("learn_asks") or []), 1)  # the next one shows instead

    def test_goal_of_a_project_goes_to_its_hub(self):
        from mnema.chat import engine as CH
        from mnema.learn.sources import Episode

        self.settings(claude_code="mixed")
        cid = "goalgoalgoal"
        CH.save_chat(
            self.v, {"id": cid, "title": "t", "messages": [{"role": "user", "text": "цель сайта"}], "updated": ""}
        )
        brain = FakeBrain(
            {
                "цель": [
                    {
                        "text": "Цель проекта «Сайт»: сдать макет к пятнице",
                        "kind": "decision",
                        "where": "decisions",
                        "confidence": 0.95,
                    }
                ]
            }
        )
        engine.learn_episodes(self.v, [Episode("mnema_chat", f"{cid}#1", "", "цель сайта")], "mnema_chat", brain=brain)
        note = self.v.find_note("projects", "Сайт")
        self.assertEqual(note.meta.get("goal", ""), "показать макет заказчику")  # a guess does not replace the goal
        brain2 = FakeBrain(
            {
                "цель": [
                    {
                        "text": "Цель проекта «Сайт» изменилась: выйти на 10 000 посетителей в месяц",
                        "kind": "decision",
                        "where": "decisions",
                        "confidence": 0.95,
                    }
                ]
            }
        )
        engine.learn_episodes(
            self.v, [Episode("mnema_chat", f"{cid}#2", "", "цель сайта изменилась")], "mnema_chat", brain=brain2
        )
        note = self.v.find_note("projects", "Сайт")
        self.assertIn("посетителей", note.meta.get("goal", ""))

    def test_one_off_instruction_is_not_a_rule(self):
        from mnema.chat import engine as CH
        from mnema.learn.sources import Episode

        self.settings(claude_code="mixed")
        cid = "rulesrules11"
        text = "Сначала собери вопросы и уточни, потом давай план. Не придумывай детали за меня."
        CH.save_chat(self.v, {"id": cid, "title": "t", "messages": [{"role": "user", "text": text}], "updated": ""})
        brain = FakeBrain(
            {
                "собери": [
                    {
                        "text": "Когда деталей мало: сначала собери вопросы и уточни, потом давай план",
                        "kind": "rule",
                        "where": "rules",
                        "confidence": 1.0,
                        "evidence": text,
                    }
                ]
            }
        )
        engine.learn_episodes(self.v, [Episode("mnema_chat", f"{cid}#1", "", text)], "mnema_chat", brain=brain)
        self.assertNotIn("собери вопросы", self.v.read_raw("70 Memory/Rules.md"))
        it = next(i for i in Ledger(self.v).items if "собери вопросы" in i["text"])
        self.assertEqual(it["state"], "weak")  # waits for a repeat instead of becoming a standing rule
        self.assertAlmostEqual(it["confidence"], 0.7)

    def test_bare_project_status_is_not_a_learned_line(self):
        from mnema.chat import engine as CH
        from mnema.learn.sources import Episode

        self.settings(claude_code="mixed")
        cid = "statusstatus"
        CH.save_chat(
            self.v, {"id": cid, "title": "t", "messages": [{"role": "user", "text": "статус проекта"}], "updated": ""}
        )
        brain = FakeBrain(
            {
                "статус": [
                    {"text": "Статус: active", "kind": "project", "where": "project:Сайт", "confidence": 0.9}
                ]
            }
        )
        engine.learn_episodes(
            self.v, [Episode("mnema_chat", f"{cid}#1", "", "статус проекта")], "mnema_chat", brain=brain
        )
        hub = self.v.read_raw("20 Projects/Сайт/_Project.md")
        self.assertNotIn("Статус: active", hub)  # the status lives in the frontmatter, the journal stays clean

    def test_correction_becomes_rule_and_respects_corrections_switch(self):
        self.go("этот отчёт слишком длинный", prev="Вот отчёт")
        self.assertIn("Отвечать без вступлений", self.v.read_raw("70 Memory/Rules.md"))
        v2 = Base()
        v2.setUp()
        try:
            v2.settings(claude_code="quiet", corrections="off")
            v2.chat(("assistant", "Вот отчёт"), ("user", "этот отчёт плохой"))
            engine.run(v2.v, brain=FakeBrain(self.TABLE))
            self.assertNotIn("Отвечать без вступлений", v2.v.read_raw("70 Memory/Rules.md"))
        finally:
            v2.tearDown()

    def test_observe_writes_nothing(self):
        r = self.go("я уверен", claude_code="observe")
        self.assertEqual((r["written"], r["observed"]), (0, 1))
        self.assertNotIn("Главный проект", self.v.read_raw("00 Inbox/Inbox.md"))

    def test_approve_mode_writes_nothing_from_elsewhere(self):
        r = self.go("я уверен", claude_code="approve")
        self.assertEqual((r["written"], r["queued"], r["observed"]), (0, 0, 1))

    def test_never_list(self):
        self.go("кофе утром")
        it = Ledger(self.v).items[0]
        engine.review(self.v, it["id"], "never")
        self.assertIn("кофе", S.load(self.v)["never"])
        self.chat(("user", "снова кофе"), ("user", "и ещё кофе"), name="c.jsonl")
        engine.run(self.v, brain=FakeBrain(self.TABLE))
        self.assertNotIn("кофе", self.v.read_raw("70 Memory/Profile.md").lower())

    def test_edit_before_keeping(self):
        cid, q = self.ask_in_chat("моя зарплата")
        engine.review(self.v, q["item"], "edit", text="Доход около 300 тысяч, нестабильный")
        self.assertIn("нестабильный", self.v.read_raw("70 Memory/Cards/Деньги.md"))

    def test_old_learned_facts_are_not_queued_for_forgetting(self):
        self.go("я уверен")
        led = Ledger(self.v)
        led.items[0]["last_seen"] = (dt.datetime.now() - dt.timedelta(days=90)).isoformat(timespec="seconds")
        led.save()
        r = engine.run(self.v, brain=FakeBrain(self.TABLE))
        self.assertEqual(r["to_forget"], 0)
        self.assertIn("Главный проект", self.v.read_raw("00 Inbox/Inbox.md"))
        self.assertFalse(Ledger(self.v).queue())

    def test_brain_failure_keeps_cursor(self):
        self.settings(claude_code="mixed")
        self.chat(("user", "Запомни, что я пробую."))

        class Broken:
            def extract(self, e, k):
                raise RuntimeError("нет сети")

        r = engine.run(self.v, brain=Broken())
        self.assertTrue(r["errors"])
        self.assertEqual(engine.run(self.v, brain=NoModelBrain())["episodes"], 1)  # retried, not lost

    def test_pause_and_off(self):
        s = self.settings(claude_code="mixed")
        s["paused"] = True
        S.save(self.v, s)
        self.chat(("user", "Запомни, что пауза работает."))
        self.assertEqual(engine.run(self.v, brain=NoModelBrain()).get("skipped"), "пауза")
        s["paused"] = False
        s["sources"]["claude_code"]["enabled"] = False
        S.save(self.v, s)
        self.assertEqual(engine.run(self.v, brain=NoModelBrain())["episodes"], 0)

    def test_demo_never_reads_the_computer(self):
        """The demo shows a prepared example; its settings keep every reading source off and runs are refused."""
        from mnema.demo import make_demo

        d = Vault(self.dir / "demo")
        make_demo(d)
        s = S.load(d)
        readers = [k for k, x in s["sources"].items() if x["enabled"] and k != "mnema_chat"]
        self.assertEqual(readers, [])
        self.assertTrue(s["demo"])
        self.assertIn("демо", engine.run(d, brain=NoModelBrain()).get("skipped", ""))
        self.assertTrue(Ledger(d).items)  # the example is there to look at

    def test_secrets_not_in_vault(self):
        s = S.load(self.v)
        s["brain"]["api_key"] = "sk-secret-777"
        S.save(self.v, s)
        self.assertNotIn("sk-secret-777", (self.v.service / "learn.json").read_text(encoding="utf-8"))
        self.assertEqual(S.load(self.v)["brain"]["api_key"], "sk-secret-777")
        self.assertNotIn("sk-secret", json.dumps(S.public(S.load(self.v))))


if __name__ == "__main__":
    unittest.main()
