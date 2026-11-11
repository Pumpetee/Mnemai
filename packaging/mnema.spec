# PyInstaller: one folder, two programs sharing it, on Windows, macOS and Linux.
#   Mnemai (.exe)      — the program (window + tray), no console
#   mnemai-cli (.exe)  — console helper: MCP server for Claude, hook, CLI commands
# macOS: the folder is wrapped into Mnemai.app.
# Build: python tools/package.py (it runs this spec)
import os
import sys

from PyInstaller.utils.hooks import collect_all

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
WIN, MAC = sys.platform == "win32", sys.platform == "darwin"
LINUX = not WIN and not MAC

datas = [
    (os.path.join(ROOT, "mnema", "ui"), "mnema/ui"),
    (os.path.join(ROOT, "mnema", "knowledge"), "mnema/knowledge"),
    (os.path.join(ROOT, "vendor", "xray"), "xray"),  # VPN keys
]
binaries, hidden = [], []
# the local model engine: its server with the libraries it loads, kept as they are in the release (a folder of its
# own, with the libraries' version links on macOS and Linux)
datas += [(os.path.join(ROOT, "vendor", "llama"), "llama")]
if WIN:
    datas += [(os.path.join(ROOT, "vendor", "webview2"), "webview2")]  # Microsoft's installer, if the component is missing
datas += [(os.path.join(ROOT, "vendor", "ocr"), "ocr")]  # the Cyrillic and Latin recognisers for scans
# local speech recognition for the meeting scribe: models, VAD asset, native libraries
# + local documents (PDF, Excel, PowerPoint) and free web search (ddgs talks to engines like a browser)
for pkg in ("faster_whisper", "ctranslate2", "onnxruntime", "av", "soundcard", "soundfile", "tokenizers",
            "pypdf", "openpyxl", "xlrd", "pptx", "ddgs", "primp", "lxml", "psutil",
            "rapidocr", "pypdfium2", "pypdfium2_raw", "shapely", "pyclipper", "omegaconf",
            "telethon", "python_socks"):  # Telegram: the owner's chats through the API, through his proxy
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hidden += h

if WIN:
    hidden += ["webview.platforms.edgechromium", "pystray._win32", "clr_loader"]
    icon = os.path.join(SPECPATH, "mnema.ico")
elif MAC:
    hidden += ["webview.platforms.cocoa", "pystray._darwin"]
    icon = os.path.join(SPECPATH, "mnema.png")  # PyInstaller makes the .icns from it
else:
    hidden += ["webview.platforms.qt", "qtpy", "PyQt6.QtWebEngineWidgets", "PyQt6.QtWebEngineCore", "PyQt6.QtWebChannel"]
    icon = None
    # Qt's window plugin needs libxcb-cursor, which a fresh Ubuntu may lack: ship it
    for d in ("/usr/lib/x86_64-linux-gnu", "/usr/lib/aarch64-linux-gnu", "/usr/lib64", "/usr/lib"):
        f = os.path.join(d, "libxcb-cursor.so.0")
        if os.path.exists(f):
            binaries.append((os.path.realpath(f), "."))
            break

# The C++ runtime stays the one on the computer. A copy from the build machine is older than what the Mesa and VAAPI
# drivers of a newer distribution need, and with it the window dies at GL start: on Fedora 44 the bundled libstdc++ has
# GLIBCXX_3.4.30, radeonsi_drv_video.so wants 3.4.32, libva fails to load and QtWebEngine aborts (SIGABRT).
SYSTEM_RUNTIME = {"libstdc++.so.6"}


def without_system_runtime(entries):
    return [e for e in entries if os.path.basename(e[0]) not in SYSTEM_RUNTIME]


binaries = without_system_runtime(binaries)

app = Analysis([os.path.join(SPECPATH, "mnema_app.py")], pathex=[ROOT], datas=datas, binaries=binaries,
               hiddenimports=hidden)
app.binaries = without_system_runtime(app.binaries)
cli = Analysis([os.path.join(SPECPATH, "mnema_cli.py")], pathex=[ROOT],
               datas=[(os.path.join(ROOT, "mnema", "ui"), "mnema/ui"), (os.path.join(ROOT, "mnema", "knowledge"), "mnema/knowledge")],
               excludes=["webview", "pystray", "PIL", "clr", "pythonnet", "faster_whisper", "ctranslate2", "onnxruntime",
                         "av", "soundcard", "soundfile", "tokenizers", "numpy", "PyQt6", "qtpy", "rapidocr", "cv2",
                         "pypdfium2", "pypdfium2_raw", "shapely", "pyclipper"])
cli.binaries = without_system_runtime(cli.binaries)

app_pyz = PYZ(app.pure)
cli_pyz = PYZ(cli.pure)

def win_version(file_name, description):
    """Version resources of a Windows program: product name Mnemai and the version, the same in every build."""
    if sys.platform != "win32":
        return None
    from PyInstaller.utils.win32.versioninfo import (
        FixedFileInfo, StringFileInfo, StringStruct, StringTable, VarFileInfo, VarStruct, VSVersionInfo)
    sys.path.insert(0, ROOT)
    from mnema import __version__

    nums = tuple(int(x) for x in (__version__.split(".") + ["0", "0", "0"])[:3]) + (0,)
    return VSVersionInfo(
        ffi=FixedFileInfo(filevers=nums, prodvers=nums),
        kids=[
            StringFileInfo([StringTable("040904B0", [
                StringStruct("ProductName", "Mnemai"),
                StringStruct("FileDescription", description),
                StringStruct("FileVersion", __version__),
                StringStruct("ProductVersion", __version__),
                StringStruct("OriginalFilename", file_name),
                StringStruct("LegalCopyright", "AGPL-3.0"),
            ])]),
            VarFileInfo([VarStruct("Translation", [0x0409, 1200])]),
        ],
    )


app_exe = EXE(app_pyz, app.scripts, [], exclude_binaries=True, name="Mnemai", icon=icon, console=False,
              version=win_version("Mnemai.exe", "Mnemai"), upx=False)
cli_exe = EXE(cli_pyz, cli.scripts, [], exclude_binaries=True, name="mnemai-cli", icon=icon, console=True,
              version=win_version("mnemai-cli.exe", "Mnemai command line"), upx=False)

coll = COLLECT(app_exe, app.binaries, app.datas, cli_exe, cli.binaries, cli.datas, name="Mnemai", upx=False)

if MAC:
    from mnema import __version__

    app_bundle = BUNDLE(
        coll,
        name="Mnemai.app",
        icon=icon,
        bundle_identifier="app.mnema.desktop",
        version=__version__,
        info_plist={
            "CFBundleName": "Mnemai",
            "CFBundleDisplayName": "Mnemai",
            "CFBundleShortVersionString": __version__,
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
            "NSMicrophoneUsageDescription": "Mnemai records meetings and voice commands when you press the microphone.",
            "NSAppleEventsUsageDescription": "Mnemai opens files and folders in Finder when you ask.",
        },
    )
