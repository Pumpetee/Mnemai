"""What differs between Windows, macOS and Linux, in one place: program names, hidden child processes, opening a folder,
the computer's memory, where other programs keep their settings, the system theme and language, a message box,
start at login and the single-instance lock. The rest of Mnemai asks here instead of checking the system itself.
"""

from __future__ import annotations

import os
import plistlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")
NAME = "windows" if IS_WIN else "macos" if IS_MAC else "linux"


def exe(name: str) -> str:
    """A program's file name on this system: «llama-server.exe» on Windows, «llama-server» elsewhere."""
    return name + ".exe" if IS_WIN else name


def quiet(low_priority: bool = False) -> dict:
    """subprocess arguments for a helper process: no console window on Windows, a lower priority if asked."""
    if IS_WIN:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if low_priority:
            flags |= getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
        return {"creationflags": flags}
    if low_priority:
        return {"preexec_fn": lambda: os.nice(5)}
    return {}


def open_path(p: Path | str) -> None:
    """Open a file or folder the way the owner would by double-clicking it."""
    p = str(p)
    if IS_WIN:
        os.startfile(p)  # noqa: S606 — the owner's own file
    else:
        subprocess.Popen(["open" if IS_MAC else "xdg-open", p], start_new_session=True)


def to_trash(p: Path | str) -> bool:
    """Move a folder to the Recycle Bin / Trash, so a deleted memory can still be brought back. True when it went."""
    p = Path(p)
    if not p.exists():
        return True
    try:
        if IS_WIN:
            import ctypes
            from ctypes import wintypes

            class SHFILEOPSTRUCTW(ctypes.Structure):
                _fields_ = [
                    ("hwnd", wintypes.HWND),
                    ("wFunc", ctypes.c_uint),
                    ("pFrom", wintypes.LPCWSTR),
                    ("pTo", wintypes.LPCWSTR),
                    ("fFlags", ctypes.c_ushort),
                    ("fAnyOperationsAborted", wintypes.BOOL),
                    ("hNameMappings", ctypes.c_void_p),
                    ("lpszProgressTitle", wintypes.LPCWSTR),
                ]

            # FO_DELETE = 3; FOF_SILENT | FOF_NOCONFIRMATION | FOF_ALLOWUNDO | FOF_NOERRORUI
            op = SHFILEOPSTRUCTW(
                None, 3, str(p.resolve()) + "\0", None, 0x0004 | 0x0010 | 0x0040 | 0x0400, False, None, None
            )
            ok = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op)) == 0 and not op.fAnyOperationsAborted
        elif sys.platform == "darwin":
            import subprocess

            script = 'tell application "Finder" to delete POSIX file "' + str(p.resolve()).replace('"', '\\"') + '"'
            ok = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=60).returncode == 0
        else:
            import subprocess

            ok = subprocess.run(["gio", "trash", str(p)], capture_output=True, timeout=60).returncode == 0
    except Exception:
        ok = False
    return ok and not p.exists()


def reveal(p: Path | str) -> None:
    """Show a file selected in its folder (Explorer, Finder); on Linux open the folder."""
    p = Path(p)
    if IS_WIN:
        subprocess.Popen(["explorer", "/select,", str(p)])
    elif IS_MAC:
        subprocess.Popen(["open", "-R", str(p)], start_new_session=True)
    else:
        open_path(p.parent if p.is_file() else p)


def ram() -> tuple[int, int]:
    """(total, available) memory in bytes; (0, 0) if the system won't say."""
    try:
        if IS_WIN:
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            m = MS()
            m.dwLength = ctypes.sizeof(MS)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
                return m.ullTotalPhys, m.ullAvailPhys
            return 0, 0
        import psutil

        v = psutil.virtual_memory()
        return v.total, v.available
    except Exception:
        return 0, 0


def config_dir(*parts: str) -> Path:
    """Where desktop programs keep their settings: %APPDATA%, ~/Library/Application Support, ~/.config."""
    if IS_WIN:
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif IS_MAC:
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base.joinpath(*parts)


def system_dark() -> bool:
    """Is the system in dark mode (the first screen opens in it before the owner picks)."""
    try:
        if IS_WIN:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            ) as k:
                return winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 0
        if IS_MAC:
            r = subprocess.run(["defaults", "read", "-g", "AppleInterfaceStyle"], capture_output=True, text=True)
            return r.stdout.strip().lower() == "dark"
        r = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"], capture_output=True, text=True
        )
        return "dark" in r.stdout
    except Exception:
        return False


def ui_lang() -> str:
    """ "ru" when the system speaks Russian, else "en"."""
    try:
        if IS_WIN:
            import ctypes

            return "ru" if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == 0x19 else "en"
        if IS_MAC:
            r = subprocess.run(["defaults", "read", "-g", "AppleLanguages"], capture_output=True, text=True)
            first = next((x.strip(' "(),') for x in r.stdout.splitlines() if x.strip(' "(),')), "")
            return "ru" if first.lower().startswith("ru") else "en"
        lang = os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG") or ""
        return "ru" if lang.lower().startswith("ru") else "en"
    except Exception:
        return "en"


def message(text: str, error: bool = False, title: str = "Mnemai") -> None:
    """A plain message box before any window exists (a failed start, a missing component)."""
    try:
        if IS_WIN:
            import ctypes

            ctypes.windll.user32.MessageBoxW(None, text, title, 0x10 if error else 0x40)
        elif IS_MAC:
            esc = text.replace("\\", "\\\\").replace('"', '\\"')
            icon = "stop" if error else "note"
            subprocess.run(
                ["osascript", "-e", f'display dialog "{esc}" with title "{title}" buttons {{"OK"}} with icon {icon}'],
                capture_output=True,
                timeout=600,
            )
        elif shutil.which("zenity"):
            subprocess.run(["zenity", "--error" if error else "--info", "--title", title, "--text", text], timeout=600)
        elif shutil.which("notify-send"):
            subprocess.run(["notify-send", title, text], timeout=10)
        else:
            print(f"{title}: {text}", file=sys.stderr)
    except Exception:
        print(f"{title}: {text}", file=sys.stderr)


# ---------------------------------------------------------------- start at login

APP_ID = "app.mnema.desktop"
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def launch_args(hidden: bool = True) -> list[str]:
    """The command that starts the program: the built app, or Python with the source tree."""
    if getattr(sys, "frozen", False):
        args = [sys.executable]
    else:
        py = Path(sys.executable)
        if IS_WIN and py.with_name("pythonw.exe").exists():
            py = py.with_name("pythonw.exe")
        args = [str(py), "-m", "mnema.desktop"]
    return args + (["--hidden"] if hidden else [])


def _mac_agent() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{APP_ID}.plist"


def _linux_entry() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "autostart" / "mnema.desktop"


def autostart_enabled() -> bool:
    if IS_WIN:
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as k:
                winreg.QueryValueEx(k, "Mnemai")
                return True
        except OSError:
            return False
    return (_mac_agent() if IS_MAC else _linux_entry()).exists()


def set_autostart(on: bool) -> None:
    args = launch_args(hidden=True)
    if IS_WIN:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if on:
                winreg.SetValueEx(k, "Mnemai", 0, winreg.REG_SZ, subprocess.list2cmdline(args))
            else:
                try:
                    winreg.DeleteValue(k, "Mnemai")
                except OSError:
                    pass
        return
    f = _mac_agent() if IS_MAC else _linux_entry()
    if not on:
        f.unlink(missing_ok=True)
        return
    f.parent.mkdir(parents=True, exist_ok=True)
    if IS_MAC:
        f.write_bytes(plistlib.dumps({"Label": APP_ID, "ProgramArguments": args, "RunAtLoad": True}))
    else:
        cmd = " ".join('"' + a.replace('"', '\\"') + '"' for a in args)
        f.write_text(
            "[Desktop Entry]\nType=Application\nName=Mnemai\nComment=Your memory for every AI\n"
            f"Exec={cmd}\nTerminal=false\nX-GNOME-Autostart-enabled=true\n",
            encoding="utf-8",
        )


# ---------------------------------------------------------------- one copy of the program

_instance = []  # keeps the lock alive for the life of the process


def first_instance(home: Path) -> bool:
    """True for the first running copy; a second launch gets False and only asks the first to show itself."""
    if IS_WIN:
        import ctypes

        _instance.append(ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\MnemaDesktopApp"))
        return ctypes.windll.kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS
    import fcntl

    home.mkdir(parents=True, exist_ok=True)
    fh = open(home / "app.lock", "w")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.close()
        return False
    _instance.append(fh)
    return True


# ---------------------------------------------------------------- a browser for printing pages to PDF


def chromium() -> str | None:
    """Edge or Chrome (or Chromium) on this computer: they print a page to PDF with no window."""
    if IS_WIN:
        for base in (
            os.environ.get("ProgramFiles(x86)"),
            os.environ.get("ProgramFiles"),
            os.environ.get("LOCALAPPDATA"),
        ):
            for rel in (
                ("Microsoft", "Edge", "Application", "msedge.exe"),
                ("Google", "Chrome", "Application", "chrome.exe"),
            ):
                if base and Path(base, *rel).exists():
                    return str(Path(base, *rel))
        return shutil.which("msedge") or shutil.which("chrome")
    if IS_MAC:
        for app in ("Google Chrome", "Microsoft Edge", "Chromium", "Brave Browser"):
            for root in (Path("/Applications"), Path.home() / "Applications"):
                p = root / f"{app}.app" / "Contents" / "MacOS" / app
                if p.exists():
                    return str(p)
        return None
    for name in (
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "microsoft-edge",
        "brave-browser",
    ):
        if shutil.which(name):
            return shutil.which(name)
    return None


# ---------------------------------------------------------------- the interface names this system

_WORD = re.compile(r"\bWindows\b")


def os_words(text: str) -> str:
    """The interface is written on Windows: «хранилище Windows», «как в Windows», «вместе с Windows». On macOS and
    Linux the same texts name that system, in every language (the keys of the translations change the same way)."""
    if IS_WIN:
        return text
    return _WORD.sub("macOS" if IS_MAC else "Linux", text)


def notify(title: str, text: str = "") -> bool:
    """A desktop notification; False when this system has no notifier (the model can still just answer)."""
    title, text = str(title)[:120], str(text)[:500]
    try:
        if IS_MAC:
            script = 'display notification ' + _applescript(text) + " with title " + _applescript(title)
            return subprocess.run(["osascript", "-e", script], capture_output=True, timeout=15).returncode == 0
        if IS_WIN:
            # PowerShell toast; works on Windows 10/11 without extra modules
            safe_t = title.replace("'", "''")
            safe_m = text.replace("'", "''")
            ps = (
                "[reflection.assembly]::LoadWithPartialName('System.Windows.Forms')|Out-Null;"
                "$n=New-Object System.Windows.Forms.NotifyIcon;"
                "$n.Icon=[System.Drawing.SystemIcons]::Information;"
                f"$n.Visible=$true;$n.ShowBalloonTip(5000,'{safe_t}','{safe_m}',"
                "[System.Windows.Forms.ToolTipIcon]::Info)"
            )
            return (
                subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=20).returncode
                == 0
            )
        for argv in (["notify-send", title, text], ["kdialog", "--passivepopup", text or title, "8", "--title", title]):
            if shutil.which(argv[0]):
                return subprocess.run(argv, capture_output=True, timeout=15).returncode == 0
    except Exception:
        return False
    return False


def _applescript(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def screenshot(dest: Path | str | None = None) -> Path | None:
    """Take a screenshot of the whole screen, save it under Pictures/Mnemai unless asked otherwise."""
    if dest is None:
        pictures = Path.home() / ("Pictures" if IS_WIN or IS_MAC else "Изображения")
        base = pictures if pictures.is_dir() else Path.home()
        dest = base / "Mnemai" / f"screenshot-{__import__('datetime').datetime.now():%Y%m%d-%H%M%S}.png"
    p = Path(dest).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        if IS_WIN:
            ps = (
                "Add-Type -AssemblyName System.Windows.Forms,System.Drawing;"
                "$b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds;"
                f"$i=New-Object System.Drawing.Bitmap $b.Width,$b.Height;"
                "$g=[System.Drawing.Graphics]::FromImage($i);"
                "$g.CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size);"
                f"$i.Save('{str(p).replace(chr(39), chr(39) * 2)}')"
            )
            if (
                subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=30).returncode
                == 0
            ):
                return p
        elif IS_MAC:
            if (
                shutil.which("screencapture")
                and subprocess.run(["screencapture", "-x", str(p)], capture_output=True, timeout=30).returncode == 0
            ):
                return p
        else:
            for argv in (
                ["grim", str(p)],
                ["spectacle", "-b", "-n", "-o", str(p)],
                ["gnome-screenshot", "-f", str(p)],
                ["scrot", "-o", str(p)],
                ["import", "-window", "root", str(p)],
            ):
                if shutil.which(argv[0]) and subprocess.run(argv, capture_output=True, timeout=30).returncode == 0:
                    return p
    except Exception:
        return None
    return None


def clipboard_get() -> str:
    """The system clipboard as text; empty string when this system has no clipboard tool."""
    try:
        if IS_MAC:
            return subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=10).stdout
        if IS_WIN:
            return subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout
        for argv in (
            ["wl-paste", "--no-newline"],
            ["xclip", "-selection", "clipboard", "-o"],
            ["xsel", "--clipboard", "--output"],
        ):
            if shutil.which(argv[0]):
                return subprocess.run(argv, capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return ""
    return ""


def clipboard_set(text: str) -> bool:
    """Put text into the system clipboard."""
    try:
        data = str(text)
        if IS_MAC:
            return subprocess.run(["pbcopy"], input=data, text=True, timeout=10).returncode == 0
        if IS_WIN:
            return subprocess.run(["clip"], input=data, text=True, timeout=10).returncode == 0
        for argv in (["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]):
            if shutil.which(argv[0]):
                # wl-copy keeps a child serving the selection; DEVNULL stops it holding our pipe open
                return (
                    subprocess.run(
                        argv,
                        input=data,
                        text=True,
                        timeout=10,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    ).returncode
                    == 0
                )
    except Exception:
        return False
    return False


def _input_tool() -> tuple[str, str] | None:
    """(backend, kind) for clicking/typing on this display; Wayland needs wtype/ydotool, X11 xdotool."""
    if IS_MAC:
        return None
    if IS_LINUX:
        for name in ("ydotool", "wtype", "xdotool"):
            if shutil.which(name):
                return name, "wayland" if name in ("ydotool", "wtype") else "x11"
    return None


def click(x: int, y: int, button: int = 1) -> bool:
    tool = _input_tool()
    if not tool:
        return False
    name = tool[0]
    try:
        if name == "xdotool":
            return (
                subprocess.run(["xdotool", "mousemove", str(x), str(y), "click", str(button)], timeout=15).returncode
                == 0
            )
        if name == "ydotool":
            return (
                subprocess.run(
                    ["ydotool", "mousemove", "--absolute", "-x", str(x), "-y", str(y)], timeout=15
                ).returncode
                == 0
                and subprocess.run(["ydotool", "click", str(button - 1)], timeout=15).returncode == 0
            )
    except Exception:
        return False
    return False


def type_text(text: str) -> bool:
    tool = _input_tool()
    if not tool:
        return False
    name = tool[0]
    try:
        if name == "xdotool":
            return subprocess.run(["xdotool", "type", "--", str(text)], timeout=30).returncode == 0
        if name == "wtype":
            return subprocess.run(["wtype", "--", str(text)], timeout=30).returncode == 0
        if name == "ydotool":
            return subprocess.run(["ydotool", "type", str(text)], timeout=30).returncode == 0
    except Exception:
        return False
    return False


KEYCODES = {
    "return": 28,
    "enter": 28,
    "esc": 1,
    "escape": 1,
    "tab": 15,
    "space": 57,
    "backspace": 14,
    "delete": 111,
    "del": 111,
    "home": 102,
    "end": 107,
    "pageup": 104,
    "pagedown": 109,
    "up": 103,
    "down": 108,
    "left": 105,
    "right": 106,
    "ctrl": 29,
    "control": 29,
    "alt": 56,
    "shift": 42,
    "super": 125,
    "meta": 125,
    "f1": 59,
    "f2": 60,
    "f3": 61,
    "f4": 62,
    "f5": 63,
    "f6": 64,
    "f7": 65,
    "f8": 66,
    "f9": 67,
    "f10": 68,
    "f11": 87,
    "f12": 88,
}


def _key_sequence(name: str) -> list[str] | None:
    """xdotool-style names → ydotool raw keycodes (e.g. ctrl+c → 29:1 46:1 46:0 29:0)."""
    codes: list[int] = []
    for part in str(name).lower().split("+"):
        part = part.strip()
        if part in KEYCODES:
            codes.append(KEYCODES[part])
        elif len(part) == 1 and part.isalnum():
            letters = {
                "q": 16,
                "w": 17,
                "e": 18,
                "r": 19,
                "t": 20,
                "y": 21,
                "u": 22,
                "i": 23,
                "o": 24,
                "p": 25,
                "a": 30,
                "s": 31,
                "d": 32,
                "f": 33,
                "g": 34,
                "h": 35,
                "j": 36,
                "k": 37,
                "l": 38,
                "z": 44,
                "x": 45,
                "c": 46,
                "v": 47,
                "b": 48,
                "n": 49,
                "m": 50,
            }
            if part in letters:
                codes.append(letters[part])
            elif part.isdigit():
                codes.append(2 + "1234567890".index(part))
            else:
                return None
        else:
            return None
    if not codes:
        return None
    out = [f"{code}:1" for code in codes] + [f"{code}:0" for code in reversed(codes)]
    return out


def key(name: str) -> bool:
    tool = _input_tool()
    if not tool:
        return False
    try:
        if tool[0] == "xdotool":
            return subprocess.run(["xdotool", "key", str(name)], timeout=15).returncode == 0
        if tool[0] == "wtype":
            return subprocess.run(["wtype", "-k", str(name)], timeout=15).returncode == 0
        if tool[0] == "ydotool":
            seq = _key_sequence(str(name))
            if not seq:
                return False
            return subprocess.run(["ydotool", "key", *seq], timeout=15).returncode == 0
    except Exception:
        return False
    return False


def scroll(amount: int) -> bool:
    tool = _input_tool()
    if not tool:
        return False
    try:
        if tool[0] == "xdotool":
            return (
                subprocess.run(
                    ["xdotool", "click", "4" if amount > 0 else "5", "--repeat", str(abs(amount))], timeout=15
                ).returncode
                == 0
            )
        if tool[0] == "ydotool":
            return subprocess.run(["ydotool", "mousemove", "--wheel", "-y", str(-amount)], timeout=15).returncode == 0
    except Exception:
        return False
    return False
