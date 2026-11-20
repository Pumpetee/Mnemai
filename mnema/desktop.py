"""Mnemai as a program: its own window, an icon in the tray (the menu bar on macOS), starts at login if you want,
learns in the background. Windows, macOS and Linux.

Closing the window hides it — learning goes on. "Выход" in the tray menu stops everything.
The window is pywebview: WebView2 on Windows, WebKit on macOS, Qt WebEngine on Linux. The tray is pystray on Windows
and macOS and Qt's own tray on Linux. The core works without any of them.
"""

from __future__ import annotations

import ctypes
import os
import signal
import time
import socket
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path


# QtWebEngine's GPU process has crashed twice on this Fedora box after a long plan, leaving a black window.
# Rendering the UI in software is a little slower but does not take the window down with the GPU process.
def _linux_webengine_flags(configured: str) -> str:
    """QtWebEngine flags for Linux: software rendering plus reduced motion.

    Software rendering leaks compositor memory for as long as a perpetual CSS animation keeps forcing frames:
    hundreds of megabytes a minute on a window nobody touches. The reduced-motion flag makes the interface stop
    endless animations (see app.css), while a custom GPU setup without --disable-gpu is left as it is.
    """
    flags = configured.strip()
    if "--disable-gpu" not in flags:
        return flags
    if "--force-prefers-reduced-motion" not in flags:
        flags = (flags + " --force-prefers-reduced-motion").strip()
    return flags


if sys.platform.startswith("linux"):
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = _linux_webengine_flags(
        os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")
    )

import webview
from PIL import Image, ImageDraw

from . import __version__, api, osapi as OS
from .cli import CONFIG, HOME
from .learn import engine, settings as S
from .learn.ledger import Ledger
from .memory import token
from .static_pages import missing_html, setup_html
from .vault import Vault
from .fsutil import read_json, write_json

APP = "Mnemai"


# ---------------------------------------------------------------- small helpers


def icon_image(size: int = 64) -> Image.Image:
    """The mark: an M on the violet square, two eyes over its outer legs. Drawn 4× and scaled down for smooth edges."""
    k = 4
    n = size * k
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, n - 1, n - 1], radius=n // 4, fill=(99, 94, 230, 255))
    u = n / 24 * 0.62  # the 24-unit drawing, 62 % of the square
    o = (n - 24 * u) / 2
    p = lambda x, y: (o + x * u, o + y * u)  # noqa: E731
    w = max(2, round(2.7 * u))
    dot = lambda x, y, r: d.ellipse([x - r, y - r, x + r, y + r], fill="white")  # noqa: E731
    for seg in ([p(5, 19.5), p(5, 9.6)], [p(5.6, 6.8), p(12, 14.2), p(18.4, 6.8)], [p(19, 9.6), p(19, 19.5)]):
        d.line(seg, fill="white", width=w, joint="curve")
        for x, y in seg:
            dot(x, y, w / 2)
    for cx in (5, 19):  # the outer corners are the eyes
        dot(*p(cx, 6.6), 2.5 * u)
    return img.resize((size, size), Image.LANCZOS)


def free_port(start: int = 7461) -> int:
    for p in range(start, start + 20):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    raise RuntimeError("нет свободного порта")


def autostart_enabled() -> bool:
    return OS.autostart_enabled()


def set_autostart(on: bool) -> None:
    OS.set_autostart(on)


AUTOSTART_LABEL = {"windows": "Запускать вместе с Windows", "macos": "Открывать при входе в macOS"}.get(
    OS.NAME, "Запускать при входе в систему"
)


def load_config() -> dict:
    return read_json(CONFIG, {}) or {}


def save_config(cfg: dict) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    write_json(CONFIG, cfg, indent=2)


# ---------------------------------------------------------------- single instance


def already_running() -> bool:
    """One copy at a time (a named mutex on Windows, a locked file elsewhere): the second launch just asks the first
    one to show its window."""
    if OS.first_instance(HOME):
        return False
    cfg = load_config()
    if cfg.get("vault") and cfg.get("port"):
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{cfg['port']}/api/app/show", headers={"X-Mnema-Token": token(Vault(cfg["vault"]))}
            )
            urllib.request.urlopen(req, timeout=3)
        except Exception:
            pass
    return True


def purge_dead_tray_icons() -> None:
    """Icons of processes killed by force stay in the tray until the mouse passes over them.
    Sweep a fake mouse move over both tray areas so Explorer drops them now."""
    if not OS.IS_WIN:
        return
    try:
        u = ctypes.windll.user32
        u.FindWindowW.restype = u.FindWindowExW.restype = ctypes.c_void_p
        areas = []
        h = u.FindWindowW("Shell_TrayWnd", None)
        for cls in ("TrayNotifyWnd", "SysPager", "ToolbarWindow32"):
            h = u.FindWindowExW(ctypes.c_void_p(h), None, cls, None) if h else None
        areas.append(h)
        h = u.FindWindowW("NotifyIconOverflowWindow", None)
        areas.append(u.FindWindowExW(ctypes.c_void_p(h), None, "ToolbarWindow32", None) if h else None)
        for h in filter(None, areas):
            r = (ctypes.c_long * 4)()
            u.GetClientRect(ctypes.c_void_p(h), r)
            for y in range(0, r[3], 4):
                for x in range(0, r[2], 4):
                    u.SendMessageW(ctypes.c_void_p(h), 0x0200, 0, (y << 16) | x)  # WM_MOUSEMOVE
    except Exception:
        pass


# ---------------------------------------------------------------- first launch


def windows_dark() -> bool:
    """The system's colour: dark or light (the first screen opens in it before the owner picks)."""
    return OS.system_dark()


def start_screen(cfg: dict) -> str:
    """What the window opens with: the memory ("vault"), the first screen ("setup") or, when the memory folder of the
    last run is gone, a screen that says so ("missing") — never a silent fresh start."""
    path = cfg.get("vault")
    if path and Path(path).exists():
        return "vault"
    return "missing" if path and not cfg.get("demo") else "setup"


def windows_lang() -> str:
    """ "ru" when the system speaks Russian, else "en"."""
    return OS.ui_lang()


# ---------------------------------------------------------------- the app


class App:
    def __init__(self, hidden: bool):
        self.hidden = hidden
        self.window = None
        self.tray = None
        self.server = None
        self.learner = None
        self.syncer = None
        self.vault: Vault | None = None
        self.port = 0
        self.quitting = False

    # -- js api (window.pywebview.api.*)
    class Api:
        def __init__(self, app: "App"):
            self._app = app

        def close_choice(self, choice: str, remember: bool = False):
            self._app.close_choice(choice, bool(remember))

        def default_path(self) -> str:
            from . import firstrun

            return firstrun.default_path()

        def pick(self, kind: str = "folder"):
            dlg = webview.FOLDER_DIALOG if kind == "folder" else webview.OPEN_DIALOG
            r = self._app.window.create_file_dialog(dlg)
            return r[0] if r else ""

        def open_existing(self, path: str):
            """«Указать, где она»: an existing memory folder opens as is; anything else says why not."""
            from . import firstrun

            err, v = firstrun.open_existing(path, self._lang())
            if err:
                return err[0]
            self._app.open_vault(v, demo=False)

        def start_new(self):
            self._app.window.load_html(setup_html())

        def _lang(self) -> str:
            return load_config().get("lang") or "en"

        def proxy_detect(self):
            from . import vpn_detect

            return vpn_detect.detect()

        def proxy_check(self, url: str, password: str = ""):
            from . import net

            return net.check(url, password or "")

        def create(self, path: str, proxy: str = "", password: str = "", prefs: dict | None = None):
            from . import firstrun

            err, v = firstrun.create(path, proxy, password, prefs)
            if err:
                return err[0]
            self._app.open_vault(v, demo=False, delay=2.4)  # the celebration on the first screen plays first

        def demo(self, proxy: str = "", password: str = "", prefs: dict | None = None):
            from . import firstrun

            err, v = firstrun.demo(proxy, password, prefs)
            if err:
                return err[0]
            self._app.open_vault(v, demo=True)

    def open_vault(self, vault: Vault, demo: bool, delay: float = 0.3) -> None:
        cfg = load_config()
        cfg.update(vault=str(vault.root), demo=demo)
        if not demo:  # the memories this computer knows: the settings switch between them
            mine = str(vault.root)
            cfg["vaults"] = [mine] + [p for p in cfg.get("vaults") or [] if Path(p) != Path(mine)][:11]
        save_config(cfg)
        self.start_server(vault)
        # let the JS call that asked for it return first, then navigate
        t = threading.Timer(delay, lambda: self.window.load_url(self.url()))
        t.daemon = True
        t.start()

    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"

    def start_server(self, vault: Vault) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.learner:
            self.learner.stop()
        self.vault = vault
        self.port = free_port()
        api.APP_HOOKS.update(
            show=self.show,
            update=self.update_api,
            update_do=self.update_do_api,
            autostart=self.autostart_api,
            info=self.info,
            switch=self.switch,
            vaults=self.vaults_api,
            vault_open=self.vault_open_api,
            vault_forget=self.vault_forget_api,
            vault_rename=self.vault_rename_api,
            close_pref=self.close_pref_api,
            quit=self.quit_api,
            open_vault=self.open_vault,
        )
        self.server = api.make_server(vault, self.port)
        threading.Thread(target=self.server.serve_forever, daemon=True, name="mnema-api").start()
        self.learner = engine.Learner(vault)
        from . import crypt

        if crypt.locked(vault.root):  # encrypted, the password is asked in the window: learning waits for it
            api.APP_HOOKS["unlocked"] = lambda: None if self.learner.is_alive() else self.learner.start()
        else:
            self.learner.start()
        self._start_sync(vault)  # BP-13: a pass soon after start, then on changes (≤ 1/10 min) and retries
        cfg = load_config()
        cfg["port"] = self.port
        try:  # the language of the screen shown if this folder is ever missing at start
            from .agent import profile as P

            cfg["lang"] = P.load(vault).get("lang") or "en"
        except Exception:
            pass
        save_config(cfg)
        self.refresh_tray()

    # -- sync in the background (BP-13)
    def _start_sync(self, vault: Vault) -> None:
        """The memory's Syncer: at start, on changes at most every 10 minutes, retry in 5 (sync.Syncer)."""
        from . import sync

        self._stop_sync()
        self.syncer = sync.Syncer(vault)
        self.syncer.start()

    def _stop_sync(self) -> None:
        s = getattr(self, "syncer", None)  # an App built without __init__ (tests) has no syncer yet
        if s:
            s.stop()
            self.syncer = None

    def sync_now(self, *_):
        """A manual sync pass from the tray menu (BP-13: вручную)."""
        from . import sync

        threading.Thread(target=lambda: sync.run(self.vault) if self.vault else None, daemon=True).start()

    def sync_indicator(self, *_) -> str:
        """The tray indicator (BP-13: индикатор в трее): the active target and its last result.

        pystray calls a menu item's text callable with the item itself, Qt's tray calls it with no arguments:
        the stray positional argument is accepted here so the tray thread never dies on a TypeError."""
        from . import sync

        if not self.vault:
            return "Синхронизация: выключена"
        t = sync.active(self.vault)
        if t is None:
            return "Синхронизация: цель не выбрана"
        r = sync.last(self.vault, t["id"])
        name = sync.NAMES.get(t["kind"], t["kind"])
        if not r:
            return f"Синхронизация: {name} — ещё не выполнялась"
        if r.get("error"):
            return f"Синхронизация: {name} — ошибка"
        if r.get("conflicts"):
            return f"Синхронизация: {name} — конфликт, обе версии сохранены"
        return f"Синхронизация: {name} — отправлено {r.get('sent', 0)}, получено {r.get('got', 0)}"

    # -- hooks for the UI
    def info(self, _=None) -> dict:
        cfg = load_config()
        return {
            "version": __version__,
            "port": self.port,
            "vault": str(self.vault.root) if self.vault else "",
            "demo": bool(cfg.get("demo")),
            "autostart": autostart_enabled(),
            "desktop": True,
            "on_close": cfg.get("on_close", "ask"),
        }

    def update_api(self, _=None) -> dict:
        """What the update button shows: the current version and the newest release for this system."""
        checker = getattr(self, "checker", None)
        return checker.state() if checker else {"desktop": False, "current": __version__, "available": False}

    def update_do_api(self, body=None) -> dict:
        """The owner's word on an update: check now, download, apply, put it off; or the quiet background flag."""
        checker = getattr(self, "checker", None)
        if not checker:
            return {"desktop": False, "available": False}
        body = body if isinstance(body, dict) else {}
        action = str(body.get("action") or "")
        if action == "check":
            return checker.check(force=True)
        if action == "download":
            return checker.download()
        if action == "later":
            return checker.later()
        if action == "auto":
            return checker.set_auto(bool(body.get("on", True)))
        if action == "apply":
            state = checker.apply()
            target = str(state.get("relaunch") or "")
            if target:  # a replaced AppImage: start the new file, then let this old process go
                try:
                    subprocess.Popen(
                        [target],
                        cwd=str(Path(target).parent),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                        env={**os.environ, "APPIMAGE": target},
                    )
                except OSError:
                    target = ""
            if state.get("restart") and not (state.get("relaunch") and not target):
                self.quit_api()  # the silent updater installs after this normal exit
            return state
        return checker.state()

    def autostart_api(self, body=None) -> dict:
        set_autostart(bool((body or {}).get("on")))
        self.refresh_tray()
        return self.info()

    def vaults_api(self, _=None) -> dict:
        """The memories this computer knows, the open one first."""
        cfg = load_config()
        cur = str(self.vault.root) if self.vault else ""
        known = cfg.get("vaults") or []
        if cur and not cfg.get("demo") and cur not in known:
            known = [cur] + known
        return {
            "current": "" if cfg.get("demo") else cur,
            "list": [
                {
                    "path": p,
                    "name": (cfg.get("names") or {}).get(p) or Path(p).name or p,
                    "exists": Vault(Path(p)).exists(),
                }
                for p in known
            ],
        }

    def vault_open_api(self, body=None) -> dict:
        p = Path(str((body or {}).get("path") or "")).expanduser()
        v = Vault(p)
        if not v.exists():
            return {"error": "Здесь нет памяти Mnemai: нет файла «70 Memory/Profile.md»."}
        self.open_vault(v, demo=False, delay=0.4)
        return {"ok": True}

    def vault_rename_api(self, body=None) -> dict:
        """The name a memory is shown with in the settings; the folder itself keeps its name."""
        b = body or {}
        cfg = load_config()
        names = cfg.get("names") or {}
        path, name = str(b.get("path") or ""), str(b.get("name") or "").strip()[:60]
        if name:
            names[path] = name
        else:
            names.pop(path, None)
        cfg["names"] = names
        save_config(cfg)
        return {"ok": True, **self.vaults_api()}

    def vault_forget_api(self, body=None) -> dict:
        """Take a memory off the list; with delete — its folder goes to the Recycle Bin. The open one is closed first:
        the window moves to the next memory on the list (or to the first screen) and then the folder goes."""
        from . import osapi

        b = body or {}
        p = Path(str(b.get("path") or ""))
        if self.vault and p.resolve() == self.vault.root.resolve():
            if not b.get("delete"):
                return {"error": "Это открытая память."}
            nxt = next((x for x in load_config().get("vaults") or [] if Path(x) != p and Vault(Path(x)).exists()), None)
            threading.Thread(target=self._close_and_delete, args=(p, nxt), daemon=True).start()
            return {"ok": True, "closing": True, "next": nxt or ""}
        if b.get("delete") and p.exists():
            if not Vault(p).exists():
                return {"error": "Здесь нет памяти Mnemai — папку не трогаю."}
            if not osapi.to_trash(p):
                return {"error": "Не получилось переместить папку в корзину. Закрой файлы из неё и повтори."}
        cfg = load_config()
        cfg["vaults"] = [x for x in cfg.get("vaults") or [] if Path(x) != p]
        save_config(cfg)
        return {"ok": True, **self.vaults_api()}

    def _close_and_delete(self, p: Path, nxt: str | None) -> None:
        """The open memory is being deleted: let the answer reach the window, close the memory, wipe the folder.
        BP-16: the folder goes only after the sync is stopped, and there is no undo."""
        from . import osapi

        time.sleep(0.4)
        self._stop_sync()  # the folder is deleted only after the sync stopped (BP-16)
        cfg = load_config()
        cfg["vaults"] = [x for x in cfg.get("vaults") or [] if Path(x) != p]
        (cfg.get("names") or {}).pop(str(p), None)
        if not nxt:
            cfg.update(vault="", demo=False)
        save_config(cfg)
        old = self.learner
        if nxt:
            self.open_vault(Vault(Path(nxt)), demo=False, delay=0.1)  # stops this memory's server and learning
        else:
            if self.server:
                self.server.shutdown()
                self.server.server_close()
                self.server = None
            if old:
                old.stop()
            self.learner = None
            self.vault = None
            self.window.load_html(setup_html())
        if old and old.is_alive():
            old.join(timeout=15)
        for _ in range(20):  # a file still held by a finishing write: try again for a while
            if osapi.to_trash(p):
                return
            time.sleep(1)
        cfg = load_config()  # couldn't: the memory comes back on the list, deleting it again shows the reason
        cfg["vaults"] = (cfg.get("vaults") or []) + [str(p)]
        save_config(cfg)

    def switch(self, _=None) -> dict:
        """Back to the first screen: create own memory instead of the demo."""
        self.window.load_html(setup_html())
        return {"ok": True}

    # -- window
    def show(self, _=None) -> dict:
        if self.window:
            self.window.show()
            self.window.restore()
        return {"ok": True}

    def on_closing(self):
        """The window's ×: ask "в трей или закрыть" (with "запомнить"), or do what was remembered."""
        if self.quitting:
            return True
        pref = load_config().get("on_close", "ask")
        if pref == "quit":
            threading.Thread(target=self.quit, daemon=True).start()
            return False
        if pref == "tray" and self.tray:
            self.window.hide()
            return False

        def ask():
            try:
                r = self.window.evaluate_js("mnemaAskClose()")  # сигнал: View объявляет функцию в 28-window.js
            except Exception:
                r = "no"
            if r != "ok":  # first-launch screen: nothing to keep alive
                self.quit()

        threading.Thread(target=ask, daemon=True).start()
        return False

    def close_choice(self, choice: str, remember: bool) -> None:
        if remember and choice in ("tray", "quit"):
            cfg = load_config()
            cfg["on_close"] = choice
            save_config(cfg)
        if choice == "tray" and self.tray:
            self.window.hide()
        elif choice == "tray":  # no tray on this desktop: hiding would lose the window
            threading.Thread(target=self.quit, daemon=True).start()
        elif choice == "quit":
            threading.Thread(target=self.quit, daemon=True).start()

    def close_pref_api(self, body=None) -> dict:
        v = str((body or {}).get("value", "ask"))
        if v in ("ask", "tray", "quit"):
            cfg = load_config()
            cfg["on_close"] = v
            save_config(cfg)
        return self.info()

    # -- tray
    def queue_size(self) -> int:
        try:
            return len(Ledger(self.vault).queue()) if self.vault else 0
        except Exception:
            return 0

    def paused(self) -> bool:
        return bool(self.vault and S.load(self.vault)["paused"])

    def toggle_pause(self, *_):
        s = S.load(self.vault)
        s["paused"] = not s["paused"]
        S.save(self.vault, s)
        self.refresh_tray()

    def learn_now(self, *_):
        if self.vault:
            from .api_learn import start_run

            start_run(self.vault)

    def toggle_autostart(self, *_):
        set_autostart(not autostart_enabled())
        self.refresh_tray()

    def quit_api(self):  # graceful stop for restarts: the tray icon goes away with the process
        t = threading.Timer(0.3, self.quit)
        t.daemon = True
        t.start()
        return {"ok": True}

    def quit(self, *_):
        self.quitting = True
        if self.learner:
            self.learner.stop()
        self._stop_sync()
        if self.tray:
            self.tray.stop()
        if self.window:
            self.window.destroy()

    def refresh_tray(self):
        if not self.tray:
            return
        self.tray.title = f"Mnemai — {'на паузе' if self.paused() else 'учится'}"
        self.tray.update_menu()

    def open_proxy(self, *_):
        self.show()
        if self.window:
            self.window.evaluate_js("mnemaOpenNet()")  # навигация View объявлена в 28-window.js

    def menu_items(self) -> list:
        """(label, action, enabled, checked) — the same menu for every tray."""

        def has(*_):
            from . import crypt

            return bool(self.vault) and not crypt.locked(self.vault.root)

        def has_sync(*_):
            from . import sync

            return bool(self.vault) and sync.active(self.vault) is not None

        return [
            ("Открыть Mnemai", lambda *_: self.show(), None, None),
            ("Учиться сейчас", self.learn_now, has, None),
            (lambda *_: "Продолжить обучение" if self.paused() else "Пауза обучения", self.toggle_pause, has, None),
            ("Прокси…", self.open_proxy, has, None),
            ("Синхронизировать сейчас", self.sync_now, has_sync, None),
            (self.sync_indicator, lambda *_: None, None, None),
            (AUTOSTART_LABEL, self.toggle_autostart, None, lambda *_: autostart_enabled()),
            None,
            ("Выход", self.quit, None, None),
        ]

    def _watch_renderer(self):
        """A renderer crash leaves a black window while the API is fine: reload the page instead of waiting for a restart.

        Two things are easy to get wrong here. The Qt bindings differ: a source install runs on PySide6 through qtpy,
        the Linux bundle ships PyQt6, so the code must not import PyQt6 by name. And in pywebview 6 the Qt window lives
        in ``window.native`` while ``window.gui`` is the platform module. Both mistakes used to hide the watchdog
        behind ``except: pass`` and the window stayed black until a manual restart.
        """
        self._renderer_reloading = False
        self._renderer_crashes: list[float] = []
        self._renderer_page = None

        def current_page():
            """The QWebEnginePage of the current window (pywebview 6: window.native.webview; older: gui.webview)."""
            native = getattr(self.window, "native", None)
            try:
                if native is not None and getattr(native, "webview", None) is not None:
                    return native.webview.page()
                return self.window.gui.webview.page()
            except Exception:  # noqa: BLE001 — the window is not created yet, or another backend
                return None

        def recover(status, code):
            if self.quitting or self._renderer_reloading or self.vault is None:
                return
            page = current_page()
            if page is None:
                _note("renderer: упал, но страница ещё недоступна — вотчдог подключится после загрузки окна")
                return
            now = time.time()
            self._renderer_crashes = [t for t in self._renderer_crashes if now - t < 600]  # 10 minutes of history
            attempt = len(self._renderer_crashes)
            self._renderer_crashes.append(now)
            delay = _renderer_reload_delay(attempt)
            slow = " (медленный режим: раз в минуту)" if delay >= RENDERER_SLOW_RELOAD_MS else ""
            _note(
                f"renderer: статус={_renderer_status_text(status)}, код={code}, "
                f"попытка {attempt + 1}, перезагрузка через {delay} мс{slow}"
            )
            self._renderer_reloading = True

            def reload_page():
                self._renderer_reloading = False
                if self.quitting:
                    return
                core = _renderer_qtcore()
                if core is None:
                    return
                try:
                    page.setUrl(core.QUrl(self.url()))
                except Exception as exc:  # noqa: BLE001 — recovery is best effort
                    _note(f"renderer: перезагрузка не удалась: {exc}")

            _renderer_schedule(delay, reload_page)

        def on_loaded(*_):
            try:
                page = current_page()
                if page is None:
                    return
                signal = getattr(page, "renderProcessTerminated", None)
                if signal is None:  # Windows (WebView2) and macOS (WebKit) have no Qt renderer signal to watch
                    return
                if page is not self._renderer_page:
                    self._renderer_page = page
                    signal.connect(recover)
                elif self._renderer_crashes:
                    _note("renderer: интерфейс восстановлен")
            except Exception as exc:  # noqa: BLE001 — the watchdog must never break the window
                _note(f"renderer: вотчдог не подключился: {exc}")

        self.window.events.loaded += on_loaded

    def _reload_ui(self) -> None:
        """Reload the page from a background thread: the crash watchdog then starts a fresh renderer."""
        try:
            self.window.evaluate_js("location.reload()")
        except Exception as exc:  # noqa: BLE001 — recovery must never end the program
            _note(f"renderer: перезагрузка страницы не удалась: {exc}")

    def _restart_renderer(self) -> None:
        """Kill the QtWebEngine renderer process: a page reload alone keeps it, and so does its native memory.

        The crash watchdog reloads the page after a renderer dies, so a new process is forked from the zygote
        and starts small. Without a renderer process (already dead, or another backend) this is a plain reload.
        """
        if getattr(self, "_renderer_page", None) is None:
            # the crash watchdog is not attached yet: killing the renderer would leave a dead page behind
            self._reload_ui()
            return
        try:
            pids = _renderer_pids(os.getpid())
        except Exception:  # noqa: BLE001 — /proc hiccups must not end the program
            pids = []
        killed = 0
        for pid in pids:
            try:
                os.kill(pid, _SIGKILL)
                killed += 1
            except OSError:  # noqa: PERF203 — the renderer may have exited between the scan and the kill
                continue
        if killed:
            # an intentional restart must not grow the crash backoff to a minute: the page is reloaded quickly
            self._renderer_crashes = []
            _note(f"renderer: память окна выше порога — перезапускаю процесс рендерера ({killed})")
        else:
            self._reload_ui()

    def _watch_memory(self):
        """Cap the renderer's native memory: a black window is worse than a page reload.

        JS heap metrics stay at a few MB while the Blink/compositor side of the renderer can grow to gigabytes
        (a huge answer, a long live table, an engine leak). Then Linux' OOM killer takes the renderer away and the
        window goes black. The chat lives on the server and an unsent draft survives a reload, so a fresh renderer
        costs only a blink.
        """
        if not OS.IS_LINUX:
            return

        def monitor():
            warned = False
            while not self.quitting:
                threading.Event().wait(RENDERER_MEMORY_CHECK_S)
                if self.quitting or not self.window:
                    return
                rss = _descendants_rss_mb(os.getpid())
                verdict = _memory_action(rss)
                if verdict == "reload":
                    _note(
                        f"renderer: память окна {rss:.0f} МБ ≥ {RENDERER_MEMORY_RELOAD_MB} МБ — "
                        "перезапускаю рендерер, страница откроется заново"
                    )
                    self._restart_renderer()
                    warned = False
                elif verdict == "warn" and not warned:
                    _note(f"renderer: память окна {rss:.0f} МБ — выше обычного, слежу")
                    warned = True
                elif verdict == "ok":
                    warned = False

        threading.Thread(target=monitor, daemon=True, name="ui-memory").start()

    def build_tray(self):
        """pystray on Windows and macOS. On Linux the window runs on Qt, so the tray is Qt's own (qt_tray, started
        with the window). A tray that can't start never stops the program: closing the window then quits."""
        if OS.IS_LINUX:
            return
        try:
            import pystray

            items = []
            for it in self.menu_items():
                if it is None:
                    items.append(pystray.Menu.SEPARATOR)
                    continue
                label, act, enabled, checked = it
                kw = {"default": True} if label == "Открыть Mnemai" else {}
                if enabled:
                    kw["enabled"] = enabled
                if checked:
                    kw["checked"] = checked
                items.append(pystray.MenuItem(label, act, **kw))
            self.tray = pystray.Icon(APP, icon_image(64), "Mnemai", pystray.Menu(*items))
            self.tray.run_detached()
        except Exception:
            self.tray = None
            return
        self._tray_ready()

    def qt_tray(self):
        """Linux: the tray icon through Qt, created in Qt's own thread once the window is up."""
        try:
            from qtpy.QtCore import QObject, Signal
            from qtpy.QtGui import QAction, QIcon, QPixmap
            from qtpy.QtWidgets import QApplication, QMenu, QSystemTrayIcon
        except Exception:
            return

        def make():
            app = QApplication.instance()
            if not app or not QSystemTrayIcon.isSystemTrayAvailable():
                return
            import io

            buf = io.BytesIO()
            icon_image(64).save(buf, "PNG")
            pm = QPixmap()
            pm.loadFromData(buf.getvalue(), "PNG")
            tray = QSystemTrayIcon(QIcon(pm), app)
            menu = QMenu()
            acts = []
            for it in self.menu_items():
                if it is None:
                    menu.addSeparator()
                    continue
                label, act, enabled, checked = it
                a = QAction(label() if callable(label) else label, menu)
                a.triggered.connect(lambda _=False, f=act: threading.Thread(target=f, daemon=True).start())
                if checked:
                    a.setCheckable(True)
                menu.addAction(a)
                acts.append((a, label, enabled, checked))

            def refresh():
                for a, label, enabled, checked in acts:
                    if callable(label):
                        a.setText(label())
                    if enabled:
                        a.setEnabled(bool(enabled()))
                    if checked:
                        a.setChecked(bool(checked()))

            menu.aboutToShow.connect(refresh)
            tray.setContextMenu(menu)
            tray.activated.connect(lambda r: self.show() if r == QSystemTrayIcon.ActivationReason.Trigger else None)
            tray.setToolTip("Mnemai")
            tray.show()
            self.tray = _QtTray(tray)

        class _Gui(QObject):  # a call from this thread runs in Qt's thread through a queued signal
            go = Signal()

            def run(self):
                make()

        app = QApplication.instance()
        if not app:
            return
        gui = _Gui()
        gui.moveToThread(app.thread())
        gui.go.connect(gui.run)
        self._qt_keep = gui
        gui.go.emit()
        self._tray_ready()

    def _tray_ready(self):
        from . import scribe_cloud

        def tray_note(text):  # meetings tell the owner where and how long, even when hidden
            try:
                self.tray.notify(text, "Mnemai")
            except Exception:
                pass

        scribe_cloud.NOTIFY[0] = tray_note

        def tick():
            while not self.quitting:
                self.refresh_tray()
                threading.Event().wait(60)

        threading.Thread(target=tick, daemon=True).start()

    def run(self):
        cfg = load_config()
        from . import upgrade

        if cfg.get("vault") and upgrade.old_layout(Path(cfg["vault"])):  # the first build's settings: clean start
            upgrade.put_aside_old_settings(HOME)
            cfg = load_config()
        try:  # подключения прежней Mnema в Claude и Cursor переходят на имя mnemai
            from .cli import migrate_mcp

            migrate_mcp()
        except Exception:  # noqa: BLE001 — чужие файлы настроек не должны мешать запуску
            pass
        vault = Vault(cfg["vault"]) if start_screen(cfg) == "vault" else None
        missing = start_screen(cfg) == "missing"
        if vault:
            self.start_server(vault)  # server first: the window opens straight on it
        self.window = webview.create_window(
            APP,
            url=self.url() if vault else None,
            html=None if vault else (missing_html(cfg["vault"], cfg.get("lang", "en")) if missing else setup_html()),
            width=1360,
            height=900,
            min_size=(960, 640),
            hidden=self.hidden,
            js_api=App.Api(self),
            background_color=("#0f1115" if windows_dark() else "#f4f3ef"),
            text_select=True,
        )
        self.window.events.closing += self.on_closing

        def fit_default_window():  # KWin/Session restore can bring an old small size back after create_window
            try:
                self.window.resize(1360, 900)
            except Exception:  # noqa: BLE001 — a lost size is not a reason to fail the launch
                pass

        self.window.events.loaded += fit_default_window
        self._watch_renderer()
        self._watch_memory()
        self.build_tray()
        from .updater import Checker, Updater

        updater = Updater(HOME, load_config)
        updater.start()
        self.updater = updater
        self.checker = Checker(
            HOME,
            load_config,
            save=save_config,
            on_installer=lambda path, digest: (
                setattr(updater, "pending", (path, digest)),
                setattr(updater, "forced", True),
            ),
        )
        self.checker.start()
        if os.environ.get("MNEMA_DEBUG_PORT"):  # developer check of the real window (localhost only)
            webview.settings["REMOTE_DEBUGGING_PORT"] = int(os.environ["MNEMA_DEBUG_PORT"])
        kw = {"gui": "qt", "func": self.qt_tray} if OS.IS_LINUX else {}
        webview.start(private_mode=False, storage_path=str(HOME / "webview"), **kw)
        try:
            updater.on_exit()
        except Exception:  # updating is optional; a failed helper must not break normal exit
            pass


def _crash_log() -> None:
    """Any failure — Python error in any thread or a hard crash — is written to app.log with the time."""
    import faulthandler
    import threading
    import traceback

    HOME.mkdir(parents=True, exist_ok=True)
    f = (HOME / "app.log").open("a", encoding="utf-8", buffering=1)

    def write(kind, exc_type, exc, tb):
        f.write(
            f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] {kind}\n"
            + "".join(traceback.format_exception(exc_type, exc, tb))
        )

    sys.excepthook = lambda t, e, tb: write("ошибка", t, e, tb)
    threading.excepthook = lambda a: write(
        f"ошибка в потоке {a.thread.name if a.thread else ''}", a.exc_type, a.exc_value, a.exc_traceback
    )
    faulthandler.enable(file=f, all_threads=True)  # hard crashes (native code) too
    _crash_log.file = f


RENDERER_SLOW_RELOAD_MS = 60_000  # после серии быстрых падений перезагружаем страницу раз в минуту, но не сдаёмся


def _renderer_status_text(status) -> str:
    """Qt's renderer termination status as a word for app.log (works with PyQt6 and PySide6 enums alike)."""
    try:
        code = int(getattr(status, "value", status))
    except (TypeError, ValueError):
        return str(status)
    return {0: "normal", 1: "abnormal", 2: "crashed", 3: "killed"}.get(code, f"unknown({code})")


def _renderer_reload_delay(attempt: int) -> int:
    """Milliseconds before reloading the page after a renderer crash.

    The first crashes get quick retries, then the watchdog slows down to one reload a minute — it never stops:
    a black window with a live API and a tray icon is worse than an occasional reload.
    """
    schedule = (400, 1500, 4000, 15000)
    return schedule[attempt] if attempt < len(schedule) else RENDERER_SLOW_RELOAD_MS


def _note(text: str) -> None:
    """One line to app.log next to Python tracebacks: the renderer recovery has no other place to report."""
    try:
        HOME.mkdir(parents=True, exist_ok=True)
        with (HOME / "app.log").open("a", encoding="utf-8", buffering=1) as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {text}\n")
    except Exception:  # noqa: BLE001 — logging must never break recovery
        pass


def _renderer_qtcore():
    """QtCore from whichever binding this install uses: qtpy (PySide6 in a source install) or PyQt6 (the bundle)."""
    try:
        from qtpy import QtCore

        return QtCore
    except ImportError:
        try:
            from PyQt6 import QtCore

            return QtCore
        except ImportError:
            return None


def _renderer_schedule(delay_ms: int, callback) -> None:
    """Arms the page reload. Kept in one function so tests can drive the watchdog without a Qt event loop."""
    core = _renderer_qtcore()
    if core is not None:
        core.QTimer.singleShot(delay_ms, callback)


def _env_number(name: str, default: int) -> int:
    """A positive integer from the environment, or the default (used by tests and by low-memory machines)."""
    try:
        value = int(os.environ.get(name, ""))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


_SIGKILL = getattr(signal, "SIGKILL", 9)  # Linux/macOS have it; Windows only imports this module, never sends it
RENDERER_MEMORY_CHECK_S = _env_number("MNEMA_RENDERER_MEM_CHECK_S", 30)  # how often the native memory is looked at
RENDERER_MEMORY_WARN_MB = _env_number("MNEMA_RENDERER_MEM_WARN_MB", 1500)  # one line in app.log above this
RENDERER_MEMORY_RELOAD_MB = _env_number("MNEMA_RENDERER_MEM_RELOAD_MB", 3000)  # reload the page above this


def _proc_children(pid: int) -> list[int]:
    """Direct children of a process from /proc (Linux); empty when the kernel does not expose them."""
    try:
        text = Path(f"/proc/{pid}/task/{pid}/children").read_text(encoding="utf-8")
    except OSError:
        return []
    return [int(part) for part in text.split() if part.isdigit()]


def _rss_mb(pid: int) -> float:
    """Resident memory of one process in MB; 0 when it is gone."""
    try:
        for line in Path(f"/proc/{pid}/status").read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024
    except (OSError, ValueError, IndexError):
        pass
    return 0.0


def _descendants_rss_mb(pid: int) -> float:
    """Native RSS of the process subtree below pid: the QtWebEngine renderer is a child of the app.

    JS heap metrics cannot see the Blink/compositor side of the renderer, so this is the number to watch.
    """
    total = 0.0
    stack, seen = [pid], set()
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        if current != pid:
            total += _rss_mb(current)
        stack.extend(_proc_children(current))
    return total


def _proc_cmdline(pid: int) -> str:
    """The command line of a process from /proc; empty when the process is already gone."""
    try:
        return Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace")
    except OSError:
        return ""


def _renderer_pids(pid: int) -> list[int]:
    """QtWebEngine renderer processes below the app — they hold the Blink/compositor memory a page reload keeps."""
    found: list[int] = []
    stack, seen = [pid], set()
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        if current != pid and "--type=renderer" in _proc_cmdline(current):
            found.append(current)
        stack.extend(_proc_children(current))
    return found


def _memory_action(rss_mb: float) -> str:
    """What to do about the renderer's native memory: ok, warn once, or reload the page."""
    if rss_mb >= RENDERER_MEMORY_RELOAD_MB:
        return "reload"
    if rss_mb >= RENDERER_MEMORY_WARN_MB:
        return "warn"
    return "ok"


WEBVIEW2 = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"


def webview2_installed() -> bool:
    """The Microsoft component that draws the window. Windows 11 has it, a clean Windows 10 may not."""
    import winreg

    keys = [
        (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{WEBVIEW2}"),
        (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{WEBVIEW2}"),
        (winreg.HKEY_CURRENT_USER, rf"Software\Microsoft\EdgeUpdate\Clients\{WEBVIEW2}"),
    ]
    for root, path in keys:
        try:
            with winreg.OpenKey(root, path) as k:
                v = str(winreg.QueryValueEx(k, "pv")[0])
                if v and v != "0.0.0.0":
                    return True
        except OSError:
            continue
    return False


def ensure_webview2() -> bool:
    """Install WebView2 with Microsoft's own installer shipped inside Mnemai (needs the internet once).
    macOS and Linux draw the window with their own engine."""
    if not OS.IS_WIN or webview2_installed():
        return True
    import subprocess

    setup = (
        Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1] / "vendor"))
        / "webview2"
        / "MicrosoftEdgeWebview2Setup.exe"
    )
    if not setup.exists():
        setup = Path(__file__).resolve().parents[1] / "vendor" / "webview2" / "MicrosoftEdgeWebview2Setup.exe"
    OS.message(
        "Для окна Mnemai нужен компонент Microsoft WebView2. Сейчас он установится — это один раз, "
        "около минуты, нужен интернет.\n\nMnemai needs the Microsoft WebView2 component. "
        "It will be installed now, once."
    )
    try:
        subprocess.run([str(setup), "/silent", "/install"], timeout=600)
    except Exception:
        pass
    if webview2_installed():
        return True
    OS.message(
        "Не получилось поставить Microsoft WebView2. Проверь интернет или поставь его вручную: "
        "https://go.microsoft.com/fwlink/p/?LinkId=2124703\n\nCould not install Microsoft WebView2.",
        error=True,
    )
    return False


def login_path() -> None:
    """A program opened from the Dock or the app menu gets a bare PATH (/usr/bin:/bin): Claude Code, Node and Ollama
    installed by the owner are not on it. Take the PATH his login shell sets up, plus the usual places."""
    if OS.IS_WIN:
        return
    import subprocess

    parts = os.environ.get("PATH", "").split(os.pathsep)
    try:
        shell = os.environ.get("SHELL") or "/bin/zsh"
        r = subprocess.run([shell, "-ilc", "printf %s \"$PATH\""], capture_output=True, text=True, timeout=8)
        parts += r.stdout.strip().splitlines()[-1].split(os.pathsep) if r.stdout.strip() else []
    except Exception:
        pass
    home = Path.home()
    parts += [
        "/opt/homebrew/bin",
        "/usr/local/bin",
        str(home / ".local" / "bin"),
        str(home / ".claude" / "local"),
        str(home / ".npm-global" / "bin"),
        str(home / ".bun" / "bin"),
        str(home / ".volta" / "bin"),
    ]
    seen, out = set(), []
    for x in parts:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    os.environ["PATH"] = os.pathsep.join(out)


class _QtTray:
    """What the rest of the app asks of a tray (title, menu refresh, a note, stop), over Qt's QSystemTrayIcon."""

    def __init__(self, icon):
        self.icon = icon

    @property
    def title(self):
        return self.icon.toolTip()

    @title.setter
    def title(self, v):
        self.icon.setToolTip(v)

    def update_menu(self):
        pass  # refreshed every time the menu opens

    def notify(self, text, title="Mnemai"):
        self.icon.showMessage(title, text)

    def stop(self):
        self.icon.hide()


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] not in ("--hidden",):
        from .cli import main as cli_main  # Mnemai.exe init/serve/... works like the CLI

        return cli_main(argv)
    if already_running():
        return
    purge_dead_tray_icons()
    _crash_log()
    login_path()
    if not ensure_webview2():
        return
    if OS.IS_WIN:
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Mnemai.Desktop")
        except Exception:
            pass
    try:
        App(hidden="--hidden" in argv).run()
    except Exception:
        import traceback

        HOME.mkdir(parents=True, exist_ok=True)
        with (HOME / "app.log").open("a", encoding="utf-8") as f:
            f.write(traceback.format_exc() + "\n")
        OS.message(f"Mnemai не смогла запуститься. Подробности записаны в файл:\n{HOME / 'app.log'}", error=True)
    finally:
        _exit_now()


def _exit_now() -> None:
    """The window is gone: stop what Mnemai started (the local model, the VPN engine) and leave. Python would otherwise
    wait for every helper thread — a library's or a request still running — and the program hangs without a window
    (seen on macOS: Mnemai stays in the Dock and «Завершить» does nothing)."""
    import atexit

    try:
        atexit._run_exitfuncs()
    except Exception:
        pass
    try:
        f = getattr(_crash_log, "file", None)
        if f:
            f.flush()
    except Exception:
        pass
    os._exit(0)


if __name__ == "__main__":
    main()
