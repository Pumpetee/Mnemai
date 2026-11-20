"""Part 4, area B (owner decisions 20.11.2026): meeting presets Private/Quality/Fast, the 5-hour recording limit,
no 300 s cap on cloud transcription, 100 MB attachments, the 10-minute question cooldown, the hourly learning timer,
Да/Нет answers to the question under a conversation, the quiz from simple to complex."""

import base64
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MNEMA_HOME", tempfile.mkdtemp())

import numpy as np  # noqa: E402

from mnema import play, scribe, scribe_cloud as SC  # noqa: E402
from mnema.agent import profile as P  # noqa: E402
from mnema.chat import attach  # noqa: E402
from mnema.learn import engine as LE, secrets_store, settings as S  # noqa: E402
from mnema.learn.ledger import Ledger  # noqa: E402
from mnema.learn.settings import _vid  # noqa: E402
from mnema.memory import init_vault, remember  # noqa: E402
from mnema.vault import Vault  # noqa: E402


class V(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.v = Vault(self.dir / "v")
        init_vault(self.v)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class TestMeetingPresets(V):
    """Решение 1: пресеты Private / Quality / Fast вместо режимов auto/local/partial/cloud."""

    def test_modes_are_the_three_presets(self):
        self.assertEqual(SC.MODES, ("private", "quality", "fast"))

    def test_default_preset_is_quality(self):
        self.assertEqual(P.load(self.v)["scribe_mode"], "quality")
        self.assertEqual(SC.settings(self.v)["mode"], "quality")

    def test_old_modes_migrate_to_presets(self):
        for old, new in (("local", "private"), ("cloud", "quality"), ("partial", "fast"), ("auto", "quality")):
            P.save(self.v, {"scribe_mode": old})
            self.assertEqual(SC.settings(self.v)["mode"], new)
        P.save(self.v, {"scribe_mode": "garbage"})
        self.assertEqual(SC.settings(self.v)["mode"], "quality")


class TestRecordLimit(V):
    """Решение 2: запись встречи длится не более 5 часов."""

    def test_limit_is_five_hours(self):
        self.assertEqual(scribe.MAX_RECORD_S, 5 * 60 * 60)

    def test_status_reports_the_limit_while_recording(self):
        s = scribe.st(self.v)
        s.clear()
        s.update(status="recording", started=time.time())
        st = scribe.status(self.v)
        self.assertEqual(st["max_seconds"], 5 * 60 * 60)
        s.clear()

    def test_limit_stop_does_nothing_when_not_recording(self):
        s = scribe.st(self.v)
        s.clear()
        scribe._limit(self.v)  # not recording: nothing happens, nothing breaks
        self.assertNotIn("status", s)


class TestCloudTimeout(V):
    """Решение 3: лимит 300 с на вызов провайдера к облачному распознаванию не применяется."""

    def test_cloud_transcription_timeout_is_not_the_provider_limit(self):
        from mnema import net

        P.save(self.v, {"scribe_base": "http://example/v1", "scribe_cloud_model": "whisper-test"})
        secrets_store.put(_vid(self.v), "scribe.cloud", "k")
        orig, calls = net.urlopen, []

        class FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps(
                    {"text": "привет", "segments": [{"start": 0.0, "end": 1.0, "text": "Привет."}]}
                ).encode()

        def fake_urlopen(req, timeout=None, **kw):
            calls.append(timeout)
            return FakeResp()

        net.urlopen = fake_urlopen
        try:
            audio = np.zeros(SC.SR * 2, dtype=np.float32)
            SC.cloud_transcribe(self.v, audio, "Я")
        finally:
            net.urlopen = orig
        self.assertEqual(calls, [600])  # the 300 s provider limit (planner) does not reach the cloud Whisper


class TestAttachments(V):
    """Решение 4: вложение — до 100 МБ; PDF/Word/Excel/изображения/текст."""

    def test_limit_is_100_mb(self):
        self.assertEqual(attach.MAX_BYTES, 100 * 1024 * 1024)

    def test_over_100_mb_is_refused_with_a_message(self):
        big = base64.b64encode(b"\0" * (attach.MAX_BYTES + 1)).decode()
        with self.assertRaises(ValueError) as e:
            attach.save(self.v, "c1", [{"name": "big.bin", "data": big}])
        self.assertIn("больше 100 МБ", str(e.exception))

    def test_formats_cover_pdf_word_excel_images_and_text(self):
        from mnema import docs

        for ext in (".pdf", ".docx", ".xlsx", ".xls", ".png", ".jpg", ".txt", ".md"):
            ok = ext in docs.SUPPORTED or ext in attach.TEXT_EXT or ext in attach.IMAGE_MIME
            self.assertTrue(ok, f"формат {ext} не читается")


class TestLearningSettings(V):
    """Решения 5–6: кулдаун вопросов 10 минут, таймер обучения раз в час."""

    def _load(self):
        (self.v.service / "learn.json").write_text('{"autodetect": true}', encoding="utf-8")
        return S.load(self.v)

    def test_question_cooldown_is_ten_minutes(self):
        self.assertEqual(S.DEFAULT["ask_cooldown_minutes"], 10)
        self.assertEqual(self._load()["ask_cooldown_minutes"], 10)

    def test_learning_timer_is_one_hour(self):
        self.assertEqual(S.DEFAULT["interval_minutes"], 60)
        self.assertEqual(self._load()["interval_minutes"], 60)


class TestAskAnswers(V):
    """Решение 7: на вопрос под разговором — «Да» (keep) и «Нет» (reject); «Позже» не обрабатывается."""

    def _pending(self, text="Люблю кофе без сахара"):
        led = Ledger(self.v)
        it, _ = led.add(
            {
                "text": text,
                "kind": "fact",
                "where": "inbox",
                "key": "",
                "tags": [],
                "confidence": 0.9,
                "source": "mnema_chat",
                "ref": "r1",
                "evidence": [],
            }
        )
        it["state"] = "pending"
        led.save()
        return it["id"]

    def test_yes_writes_the_fact(self):
        i = self._pending()
        LE.review(self.v, i, "keep")  # «Да»
        self.assertEqual(Ledger(self.v).get(i)["state"], "confirmed")
        self.assertIn("Люблю кофе без сахара", self.v.read_raw("00 Inbox/Inbox.md") or "")

    def test_no_rejects_without_writing(self):
        i = self._pending()
        LE.review(self.v, i, "reject")  # «Нет»
        self.assertEqual(Ledger(self.v).get(i)["state"], "rejected")
        self.assertNotIn("Люблю кофе без сахара", self.v.read_raw("00 Inbox/Inbox.md") or "")

    def test_no_later_option_is_processed(self):
        i = self._pending()
        with self.assertRaises(ValueError):
            LE.review(self.v, i, "later")  # «Позже» не существует: только «Да / Нет»


class TestQuizOrder(V):
    """Решение 8: квиз идёт от простого к сложному (существующая мера — длина факта)."""

    def test_quiz_goes_from_simple_to_complex(self):
        P.save(self.v, {"memory_on": True})
        for i, text in enumerate(
            ["Кофе без сахара", "Работаю продактом в финтехе", "Живу в Лиссабоне у моря круглый год"]
        ):
            remember(self.v, text, f"card:Т{i}", "owner")
        q = play.quiz(self.v, size=3)
        lens = [len(x["text"]) for x in q["items"]]
        self.assertEqual(lens, sorted(lens))  # короткие (простые) факты — первыми
        self.assertEqual(len(q["items"]), 3)


if __name__ == "__main__":
    unittest.main()
