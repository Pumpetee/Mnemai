"""The renderer watchdog of the desktop window (mnema/desktop.py) — the part that keeps a dead QtWebEngine renderer
from leaving a black window: status names, reload backoff, app.log note, attaching to the page and reloading it."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mnema import desktop as D  # noqa: E402


class RendererStatusAndDelay(unittest.TestCase):
    def test_status_has_a_word_for_every_qt_code(self):
        for code, name in ((0, "normal"), (1, "abnormal"), (2, "crashed"), (3, "killed")):
            self.assertEqual(D._renderer_status_text(code), name)
        self.assertEqual(D._renderer_status_text(9), "unknown(9)")

    def test_status_accepts_enum_like_objects(self):
        class Enum:
            value = 2

        self.assertEqual(D._renderer_status_text(Enum()), "crashed")
        self.assertEqual(D._renderer_status_text(None), "None")

    def test_reload_delays_grow_then_stay_at_one_a_minute(self):
        self.assertEqual([D._renderer_reload_delay(i) for i in range(4)], [400, 1500, 4000, 15000])
        self.assertEqual(D._renderer_reload_delay(4), D.RENDERER_SLOW_RELOAD_MS)
        self.assertEqual(D._renderer_reload_delay(4), 60_000)
        self.assertEqual(D._renderer_reload_delay(100), 60_000)


class RendererNote(unittest.TestCase):
    def test_note_goes_to_app_log_with_a_time(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(D, "HOME", Path(tmp)):
            D._note("renderer: проверка")
            text = (Path(tmp) / "app.log").read_text(encoding="utf-8")
        self.assertIn("renderer: проверка", text)
        self.assertRegex(text, r"^\[\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\] ")

    def test_unwritable_log_never_raises(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(D, "HOME", Path(tmp) / "no" / "such" / "dir"):
            with mock.patch.object(Path, "mkdir", side_effect=OSError("read-only")):
                D._note("renderer: некуда писать")  # must not raise


class _Signal:
    def __init__(self):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)


class _Page:
    def __init__(self):
        self.renderProcessTerminated = _Signal()
        self.urls = []

    def setUrl(self, url):
        self.urls.append(url.toString())


class _WebView:
    def __init__(self, page):
        self._page = page

    def page(self):
        return self._page


class _Native:
    def __init__(self, page):
        self.webview = _WebView(page)


class _LoadedEvent:
    def __init__(self):
        self.slot = None

    def __iadd__(self, slot):
        self.slot = slot
        return self


class _Events:
    def __init__(self):
        self.loaded = _LoadedEvent()


class _Window:
    def __init__(self, page):
        self.native = _Native(page)
        self.events = _Events()


class RendererWatchdog(unittest.TestCase):
    """Drives _watch_renderer with a fake window so no Qt event loop is needed."""

    def setUp(self):
        self.app = D.App.__new__(D.App)  # no __init__: the watchdog only needs window, vault, quitting, url
        self.page = _Page()
        self.app.window = _Window(self.page)
        self.app.vault = object()
        self.app.quitting = False
        self.app.url = lambda: "http://127.0.0.1:7461/"
        self.app._renderer_page = None
        self.scheduled = []
        self.notes = []
        self.schedule_patch = mock.patch.object(
            D, "_renderer_schedule", side_effect=lambda delay, callback: self.scheduled.append((delay, callback))
        )
        self.note_patch = mock.patch.object(D, "_note", side_effect=self.notes.append)
        self.schedule_patch.start()
        self.note_patch.start()
        self.addCleanup(self.schedule_patch.stop)
        self.addCleanup(self.note_patch.stop)
        self.app._watch_renderer()

    def _load(self):
        self.app.window.events.loaded.slot()

    def test_watchdog_attaches_when_the_page_is_ready(self):
        self._load()
        self.assertEqual(len(self.page.renderProcessTerminated.slots), 1)
        self.assertIn("renderer: вотчдог подключён", self.notes)

    def test_renderer_crash_schedules_a_reload_and_logs_it(self):
        self._load()
        crash = self.page.renderProcessTerminated.slots[0]
        crash(2, 9)  # crashed, SIGKILL
        self.assertEqual([delay for delay, _ in self.scheduled], [400])
        self.assertTrue(any("renderer: статус=crashed" in note for note in self.notes))
        self.assertTrue(any("код=9" in note for note in self.notes))

        delay, reload_page = self.scheduled.pop()
        reload_page()
        self.assertEqual(self.page.urls, ["http://127.0.0.1:7461/"])
        self.assertFalse(self.app._renderer_reloading)

    def test_second_crash_waits_longer_and_crashes_are_not_lost(self):
        self._load()
        crash = self.page.renderProcessTerminated.slots[0]
        crash(2, 1)
        self.app._renderer_reloading = False  # the test does not run the scheduled callback between crashes
        crash(2, 1)
        self.assertEqual([delay for delay, _ in self.scheduled], [400, 1500])

    def test_watchdog_does_not_fire_after_quit_or_without_a_vault(self):
        self._load()
        crash = self.page.renderProcessTerminated.slots[0]
        self.app.quitting = True
        crash(2, 1)
        self.app.quitting = False
        self.app.vault = None
        crash(2, 1)
        self.assertEqual(self.scheduled, [])

    def test_loaded_after_crash_says_the_interface_is_back(self):
        self._load()
        crash = self.page.renderProcessTerminated.slots[0]
        crash(2, 1)
        self._load()  # page loaded again after the reload
        self.assertIn("renderer: интерфейс восстановлен", self.notes)

    def test_page_without_the_qt_signal_is_left_alone(self):
        """Windows (WebView2) and macOS (WebKit) have no QWebEnginePage signal; the watchdog must not raise there."""
        page = mock.Mock(spec=[])  # no renderProcessTerminated at all
        page.webview = mock.Mock()
        self.app.window.native.webview.page = lambda: page
        self._load()  # must not raise
        self.assertIsNone(self.app._renderer_page)

    def test_watchdog_failure_does_not_break_the_window(self):
        self.page.renderProcessTerminated.connect = mock.Mock(side_effect=RuntimeError("сломался Qt"))
        self._load()  # the exception inside the event handler is logged, not raised
        self.assertTrue(any("вотчдог не подключился" in note for note in self.notes))


if __name__ == "__main__":
    unittest.main()
