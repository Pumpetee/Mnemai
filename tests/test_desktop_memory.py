"""The renderer memory watchdog of the desktop window (mnema/desktop.py): native RSS of the renderer subtree,
its warn/reload thresholds, the reload itself and the monitor loop that drives them."""

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mnema import desktop as D  # noqa: E402


class EnvNumbers(unittest.TestCase):
    def test_positive_numbers_override_the_default(self):
        with mock.patch.dict(D.os.environ, {"MNEMA_TEST_N": "42"}):
            self.assertEqual(D._env_number("MNEMA_TEST_N", 7), 42)

    def test_junk_and_zero_fall_back_to_the_default(self):
        for raw in ("", "abc", "0", "-5"):
            with mock.patch.dict(D.os.environ, {"MNEMA_TEST_N": raw}):
                self.assertEqual(D._env_number("MNEMA_TEST_N", 7), 7)
        with mock.patch.dict(D.os.environ, {}, clear=False):
            D.os.environ.pop("MNEMA_TEST_N", None)
            self.assertEqual(D._env_number("MNEMA_TEST_N", 7), 7)


class MemoryAction(unittest.TestCase):
    def test_thresholds(self):
        self.assertEqual(D._memory_action(0), "ok")
        self.assertEqual(D._memory_action(D.RENDERER_MEMORY_WARN_MB - 1), "ok")
        self.assertEqual(D._memory_action(D.RENDERER_MEMORY_WARN_MB), "warn")
        self.assertEqual(D._memory_action(D.RENDERER_MEMORY_RELOAD_MB - 1), "warn")
        self.assertEqual(D._memory_action(D.RENDERER_MEMORY_RELOAD_MB), "reload")
        self.assertEqual(D._memory_action(99999), "reload")


class RendererSubtree(unittest.TestCase):
    def test_descendants_rss_excludes_the_app_itself(self):
        tree = {1: [2, 3], 2: [4], 3: [], 4: []}
        rss = {1: 100, 2: 50, 3: 25, 4: 10}
        with (
            mock.patch.object(D, "_proc_children", side_effect=lambda p: tree.get(p, [])),
            mock.patch.object(D, "_rss_mb", side_effect=lambda p: rss.get(p, 0)),
        ):
            self.assertEqual(D._descendants_rss_mb(1), 85)

    def test_a_gone_process_contributes_nothing(self):
        with (
            mock.patch.object(D, "_proc_children", return_value=[7]),
            mock.patch.object(D, "_rss_mb", return_value=0.0),
        ):
            self.assertEqual(D._descendants_rss_mb(1), 0.0)

    def test_this_process_is_visible_in_proc(self):
        if not Path("/proc").exists():
            self.skipTest("нет /proc")
        self.assertGreater(D._rss_mb(os.getpid()), 0)
        self.assertGreaterEqual(D._descendants_rss_mb(os.getpid()), 0.0)


class WebEngineFlags(unittest.TestCase):
    def test_software_rendering_also_forces_reduced_motion(self):
        self.assertEqual(
            D._linux_webengine_flags("--disable-gpu"),
            "--disable-gpu --force-prefers-reduced-motion",
        )

    def test_custom_flags_are_kept_and_the_motion_flag_appended(self):
        self.assertEqual(
            D._linux_webengine_flags("--disable-gpu --foo=bar"),
            "--disable-gpu --foo=bar --force-prefers-reduced-motion",
        )

    def test_flag_is_not_added_twice(self):
        flags = "--disable-gpu --force-prefers-reduced-motion"
        self.assertEqual(D._linux_webengine_flags(flags), flags)

    def test_gpu_rendering_is_left_alone(self):
        self.assertEqual(D._linux_webengine_flags("--use-gl=egl"), "--use-gl=egl")
        self.assertEqual(D._linux_webengine_flags(""), "")

    def test_the_interface_really_stops_endless_animations(self):
        css = (Path(__file__).resolve().parents[1] / "mnema/ui/css/app.css").read_text(encoding="utf-8")
        block = css[css.rfind("@media (prefers-reduced-motion: reduce)") :]
        self.assertIn("animation-iteration-count: 1 !important", block)
        self.assertIn("*::before", block)


class RendererProcesses(unittest.TestCase):
    def test_renderer_pids_finds_only_renderers(self):
        tree = {1: [2, 3], 2: [4], 3: [], 4: []}
        cmdlines = {
            2: "--type=zygote --no-zygote-sandbox",
            3: "/usr/lib64/qt6/libexec/QtWebEngineProcess --type=renderer",
            4: "helper",
        }
        with (
            mock.patch.object(D, "_proc_children", side_effect=lambda p: tree.get(p, [])),
            mock.patch.object(D, "_proc_cmdline", side_effect=lambda p: cmdlines.get(p, "")),
        ):
            self.assertEqual(sorted(D._renderer_pids(1)), [3])

    def test_a_gone_renderer_is_skipped(self):
        with (
            mock.patch.object(D, "_proc_children", return_value=[9]),
            mock.patch.object(
                D, "_proc_cmdline", return_value="/usr/lib64/qt6/libexec/QtWebEngineProcess --type=renderer"
            ),
        ):
            self.assertEqual(D._renderer_pids(1), [9])


class RendererRestart(unittest.TestCase):
    def _app(self):
        app = D.App.__new__(D.App)
        app._renderer_page = object()  # the crash watchdog is attached
        app._reload_ui = mock.Mock()
        return app

    def test_restart_renderer_kills_the_processes(self):
        app = self._app()
        app._renderer_crashes = [1.0, 2.0]  # a slow crash backoff from earlier failures must not delay the reload
        with (
            mock.patch.object(D, "_renderer_pids", return_value=[11, 22]),
            mock.patch.object(D.os, "kill") as kill,
            mock.patch.object(D, "_note") as note,
        ):
            app._restart_renderer()
        self.assertEqual(kill.call_args_list, [mock.call(11, D._SIGKILL), mock.call(22, D._SIGKILL)])
        self.assertTrue(any("перезапускаю процесс рендерера (2)" in str(c.args[0]) for c in note.call_args_list))
        self.assertEqual(app._renderer_crashes, [])
        app._reload_ui.assert_not_called()

    def test_restart_renderer_falls_back_to_a_reload(self):
        app = self._app()
        with mock.patch.object(D, "_renderer_pids", return_value=[]):
            app._restart_renderer()
        app._reload_ui.assert_called_once()
        self.assertIsNotNone(app._renderer_page)  # untouched; the fallback only reloads the page

    def test_without_the_watchdog_it_only_reloads(self):
        app = self._app()
        app._renderer_page = None
        with mock.patch.object(D, "_renderer_pids") as pids:
            app._restart_renderer()
        pids.assert_not_called()
        app._reload_ui.assert_called_once()


class UiReload(unittest.TestCase):
    def test_reload_ui_reloads_the_page(self):
        app = D.App.__new__(D.App)
        app.window = mock.Mock()
        D.App._reload_ui(app)
        app.window.evaluate_js.assert_called_once_with("location.reload()")

    def test_failed_reload_is_logged_not_raised(self):
        app = D.App.__new__(D.App)
        app.window = mock.Mock()
        app.window.evaluate_js.side_effect = RuntimeError("окно закрылось")
        with mock.patch.object(D, "_note") as note:
            D.App._reload_ui(app)
        self.assertTrue(any("перезагрузка страницы не удалась" in str(c.args[0]) for c in note.call_args_list))


class MemoryWatch(unittest.TestCase):
    def test_watch_memory_is_linux_only(self):
        app = D.App.__new__(D.App)
        app.quitting = True
        app.window = object()
        with mock.patch.object(D.OS, "IS_LINUX", False), mock.patch.object(D, "_note") as note:
            app._watch_memory()
        note.assert_not_called()

    def test_watch_memory_starts_a_named_daemon_thread_and_says_so(self):
        app = D.App.__new__(D.App)
        app.quitting = True
        app.window = object()
        started = []

        class FakeThread:
            def __init__(self, **kwargs):
                started.append(kwargs)

            def start(self):
                pass

        with (
            mock.patch.object(D.OS, "IS_LINUX", True),
            mock.patch.object(D, "_note") as note,
            mock.patch.object(D.threading, "Thread", FakeThread),
        ):
            app._watch_memory()
        self.assertEqual(started[0]["name"], "ui-memory")
        self.assertTrue(started[0]["daemon"])
        note.assert_not_called()  # a clean start writes nothing to app.log: the GUI smoke test demands a clean log

    def test_monitor_warns_once_and_restarts_the_renderer_at_the_cap(self):
        app = D.App.__new__(D.App)
        app.quitting = False
        app.window = object()
        notes = []
        sequence = iter([1600, 1700, 700, 3300])  # warn, still slow but only one note, back to normal, above the cap

        class FakeEvent:
            def wait(self, seconds):
                return None

        class SyncThread:
            def __init__(self, **kwargs):
                self.target = kwargs.get("target")

            def start(self):
                self.target()

        def fake_reload():
            app.quitting = True

        app._restart_renderer = fake_reload
        with (
            mock.patch.object(D.OS, "IS_LINUX", True),
            mock.patch.object(D, "_descendants_rss_mb", side_effect=lambda _pid: next(sequence)),
            mock.patch.object(D, "_note", side_effect=notes.append),
            mock.patch.object(D.threading, "Event", FakeEvent),
            mock.patch.object(D.threading, "Thread", SyncThread),
        ):
            app._watch_memory()
        self.assertEqual(len([n for n in notes if "выше обычного" in n]), 1)
        self.assertEqual(len([n for n in notes if "перезапускаю рендерер" in n]), 1)
        self.assertTrue(app.quitting)


if __name__ == "__main__":
    unittest.main()
