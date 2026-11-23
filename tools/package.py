"""Mnemai packager: looks at the operating system it runs on and builds the package for it.

    python tools/package.py              # build for this system
    python tools/package.py --skip-tests

The target computer is assumed to have nothing installed: no Python, no runtimes. Everything the program needs is
inside the package; what Windows itself must provide is checked against what a clean Windows 10/11 has.

Windows  → dist/Mnemai-Setup-<version>.exe (installer) and dist/Mnemai-<version>-windows-x64.zip (portable)
macOS    → dist/Mnemai-<version>-macos-<arm64|x64>.dmg — Mnemai.app, drag it to Applications
Linux    → dist/Mnemai-<version>-<x86_64|aarch64>.AppImage (one file, with its .zsync for updates) and the same as a
           .tar.gz folder (Mnemai-<version>-linux-<arch>.tar.gz)

Every package is started once after the build: its own CLI makes a memory folder and serves it, and the local model
engine inside answers --version. Each file gets a .sha256 beside it.
"""

from __future__ import annotations

import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VC_RUNTIME = ("vcruntime", "msvcp", "concrt", "vcomp", "vccorlib")  # not part of a clean Windows


def say(msg: str) -> None:
    print(f"[package] {msg}", flush=True)


def version() -> str:
    from mnema import __version__

    return __version__


def venv_python() -> Path:
    py = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return py if py.exists() else Path(sys.executable)


# ---------------------------------------------------------------- Windows


def windows_prerequisites() -> None:
    llama = ROOT / "vendor" / "llama"
    if not (llama / "llama-server.exe").exists():
        raise SystemExit("нет движка локальной модели: положи сборку llama.cpp (CPU, x64) в vendor/llama")
    sysdir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32"
    for name in ("msvcp140.dll", "vcruntime140.dll", "vcruntime140_1.dll"):  # the engine needs them next to itself
        if not (llama / name).exists():
            shutil.copy2(sysdir / name, llama / name)
            say(f"добавил {name} к движку локальной модели")
    wv = ROOT / "vendor" / "webview2" / "MicrosoftEdgeWebview2Setup.exe"
    if not wv.exists():
        import urllib.request
        from mnema import net

        wv.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(
            "https://go.microsoft.com/fwlink/p/?LinkId=2124703", headers={"User-Agent": "Mnemai"}
        )
        wv.write_bytes(net.urlopen(req, timeout=120).read())
        say("скачал установщик Microsoft WebView2")


def check_windows_dependencies(app: Path) -> list[str]:
    """Every DLL a binary imports must be next to it, inside the bundle, or part of a clean Windows."""
    import pefile

    sysdir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32"
    internal = app / "_internal"
    bundle = {p.name.lower() for p in internal.rglob("*") if p.suffix.lower() in (".dll", ".pyd")}
    problems = []
    for p in app.rglob("*"):
        if p.suffix.lower() not in (".dll", ".pyd", ".exe"):
            continue
        try:
            pe = pefile.PE(str(p), fast_load=True)
            pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
        except Exception:
            continue
        own = {x.name.lower() for x in p.parent.iterdir()}
        separate = "llama" in p.relative_to(app).parts  # a program of its own: sees only its folder
        for e in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
            n = e.dll.decode(errors="replace").lower()
            if n in own or (not separate and n in bundle) or n.startswith(("api-ms-win", "ext-ms-")):
                continue
            if (sysdir / n).exists() and not n.startswith(VC_RUNTIME):
                continue
            problems.append(f"{p.relative_to(app)} → {n}")
    return problems


README = """Mnemai {v} — память о тебе для любого ИИ / your memory for any AI

ВАЖНО: сначала распакуйте ВСЮ папку на диск («Извлечь всё» / Extract all), потом запускайте
Mnemai.exe из неё. Не запускайте Mnemai.exe прямо из окна архива (ZIP, WinRAR, 7-Zip):
тогда Windows покажет ошибку «Failed to load Python DLL … python313.dll» — это не поломка
программы, а неполная распаковка.
Ещё проще: скачайте установщик Mnemai-Setup.exe с github.com/Pumpetee/Mnemai/releases —
он поставит программу сам.

IMPORTANT: extract the whole folder to disk first («Extract all»), then run Mnemai.exe from
that folder. Do not run Mnemai.exe straight from the archive window (ZIP, WinRAR, 7-Zip): Windows
then says «Failed to load Python DLL … python313.dll» — that is an incomplete extraction, not a
broken program. Even easier: get the Mnemai-Setup.exe installer from
github.com/Pumpetee/Mnemai/releases — it installs the program for you.

Ничего заранее ставить не нужно. Если в Windows нет компонента Microsoft WebView2,
Mnemai поставит его сама при первом запуске (нужен интернет, один раз).

Nothing to install beforehand. If Windows lacks Microsoft WebView2, Mnemai installs it on first
start (internet needed once).

Windows 10 / 11, 64-bit.
Данные / data: ~/.mnema (настройки) и папка памяти, которую выберешь при первом запуске.
"""


def build_windows(skip_tests: bool) -> Path:
    py = venv_python()
    windows_prerequisites()
    if not skip_tests:
        say("тесты")
        r = subprocess.run(
            [str(py), "-m", "unittest", "discover", "-s", "tests", "-q"], cwd=ROOT, capture_output=True, text=True
        )
        if r.returncode:
            print(r.stderr[-3000:])
            raise SystemExit("тесты не прошли — пакет не собираю")
    out = ROOT / "dist"
    work = ROOT / "build-package"
    shutil.rmtree(out / "Mnemai", ignore_errors=True)
    say("сборка программы (PyInstaller)")
    subprocess.run(
        [
            str(py),
            "-m",
            "PyInstaller",
            "packaging/mnema.spec",
            "--noconfirm",
            "--distpath",
            str(out),
            "--workpath",
            str(work),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    app = out / "Mnemai"
    problems = check_windows_dependencies(app)
    if problems:
        print("\n".join(problems[:40]))
        raise SystemExit("в пакете не хватает библиотек — см. список выше")
    say("зависимости: всё внутри пакета или есть в любой Windows 10/11")
    (app / "README.txt").write_text(README.format(v=version()), encoding="utf-8")
    (app / "version.txt").write_text(version(), encoding="utf-8")  # the installer's detector reads it
    z = out / f"Mnemai-{version()}-windows-x64.zip"
    z.unlink(missing_ok=True)
    say("архив")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        # the instruction goes into the archive first: a person who opens the ZIP sees it before Mnemai.exe
        readme = app / "README.txt"
        zf.write(readme, Path("Mnemai") / "ПРОЧТИ ПЕРВЫМ — как запустить.txt")
        zf.write(readme, Path("Mnemai") / "README.txt")
        for p in sorted(app.rglob("*")):
            if p.is_file() and p != readme:
                zf.write(p, Path("Mnemai") / p.relative_to(app))
    h = hashlib.sha256(z.read_bytes()).hexdigest()
    (out / (z.name + ".sha256")).write_text(f"{h}  {z.name}\n", encoding="utf-8")
    say(f"готово: {z} · {z.stat().st_size / 1e6:.0f} МБ · sha256 {h[:16]}…")
    build_installer()
    return z


def iscc() -> Path | None:
    for p in [
        os.environ.get("ISCC", ""),
        str(ROOT.parents[1] / "tools" / "InnoSetup6" / "ISCC.exe"),  # a portable Inno Setup beside the apps folder
        str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe"),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]:
        if p and Path(p).is_file():
            return Path(p)
    return None


def build_installer() -> Path | None:
    """dist/Mnemai-Setup-<version>.exe — installs for the user, finds and clears older versions (packaging/mnema.iss)."""
    c = iscc()
    if not c:
        say("установщик не собран: нет Inno Setup 6 (ISCC.exe). Поставь его или укажи путь в ISCC")
        return None
    say("установщик (Inno Setup)")
    r = subprocess.run(
        [str(c), f"/DAppVersion={version()}", "/Q", str(ROOT / "packaging" / "mnema.iss")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise SystemExit("установщик не собрался")
    exe = ROOT / "dist" / f"Mnemai-Setup-{version()}.exe"
    h = hashlib.sha256(exe.read_bytes()).hexdigest()
    (exe.parent / (exe.name + ".sha256")).write_text(f"{h}  {exe.name}\n", encoding="utf-8")
    say(f"готово: {exe} · {exe.stat().st_size / 1e6:.0f} МБ · sha256 {h[:16]}…")
    return exe


# ---------------------------------------------------------------- macOS and Linux


def run_tests(py: Path) -> None:
    say("тесты")
    r = subprocess.run(
        [str(py), "-m", "unittest", "discover", "-s", "tests", "-q"], cwd=ROOT, capture_output=True, text=True
    )
    if r.returncode:
        print(r.stderr[-3000:])
        raise SystemExit("тесты не прошли — пакет не собираю")


def pyinstaller(py: Path) -> Path:
    out, work = ROOT / "dist", ROOT / "build-package"
    shutil.rmtree(out / "Mnemai", ignore_errors=True)
    shutil.rmtree(out / "Mnemai.app", ignore_errors=True)
    from mnema.desktop import icon_image

    icon_image(512).save(ROOT / "packaging" / "mnema.png")
    say("сборка программы (PyInstaller)")
    r = subprocess.run(
        [
            str(py),
            "-m",
            "PyInstaller",
            "packaging/mnema.spec",
            "--noconfirm",
            "--distpath",
            str(out),
            "--workpath",
            str(work),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if r.returncode:
        print(r.stdout[-4000:], r.stderr[-6000:])
        raise SystemExit("PyInstaller не собрал программу")
    return out


def smoke(folder: Path, cli: Path) -> None:
    """The built package works on its own: its CLI makes a memory and serves it; its local model engine starts."""
    import json
    import tempfile
    import time
    import urllib.request

    llama = next(folder.rglob("llama-server"), None)
    if not llama:
        raise SystemExit("в пакете нет движка локальной модели")
    r = subprocess.run([str(llama), "--version"], capture_output=True, text=True, timeout=60)
    if r.returncode:
        raise SystemExit(f"движок локальной модели в пакете не запускается: {(r.stderr or r.stdout)[-600:]}")
    say("проверка: движок локальной модели запускается")
    tmp = Path(tempfile.mkdtemp(prefix="mnema-smoke-"))
    env = dict(os.environ, MNEMA_HOME=str(tmp / "home"), MNEMA_NO_DETECT="1")
    subprocess.run([str(cli), "init", str(tmp / "memory"), "--default"], check=True, env=env, timeout=120)
    token = (tmp / "memory" / ".mnema" / "token").read_text(encoding="utf-8").strip()
    srv = subprocess.Popen([str(cli), "--vault", str(tmp / "memory"), "serve", "--port", "7493"], env=env)
    try:
        for _ in range(60):
            time.sleep(1)
            try:
                req = urllib.request.Request(
                    "http://127.0.0.1:7493/api/ping", headers={"X-Mnema-Token": token, "Host": "127.0.0.1:7493"}
                )
                with urllib.request.urlopen(req, timeout=3) as resp:
                    ping = json.loads(resp.read())
                    if ping.get("ok"):
                        say(f"проверка: память создана и отдаётся, версия {ping.get('version')}")
                        return
            except OSError:
                continue
        raise SystemExit("собранная программа не отвечает")
    finally:
        srv.terminate()


def sha_file(f: Path) -> None:
    h = hashlib.sha256(f.read_bytes()).hexdigest()
    (f.parent / (f.name + ".sha256")).write_text(f"{h}  {f.name}\n", encoding="utf-8")
    say(f"готово: {f} · {f.stat().st_size / 1e6:.0f} МБ · sha256 {h[:16]}…")


def build_macos(skip_tests: bool) -> Path:
    py = venv_python()
    if not (ROOT / "vendor" / "llama" / "llama-server").exists():
        raise SystemExit("нет движка локальной модели: python tools/fetch_vendor.py")
    if not skip_tests:
        run_tests(py)
    out = pyinstaller(py)
    app = out / "Mnemai.app"
    say("подпись (ad-hoc): без неё Apple Silicon не запускает программу")
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(app)], check=True)
    smoke(app, app / "Contents" / "MacOS" / "mnemai-cli")
    arch = "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "x64"
    dmg = out / f"Mnemai-{version()}-macos-{arch}.dmg"
    dmg.unlink(missing_ok=True)
    stage = out / "dmg"
    shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir()
    subprocess.run(["ditto", str(app), str(stage / "Mnemai.app")], check=True)
    (stage / "Applications").symlink_to("/Applications")
    say("образ диска (DMG)")
    subprocess.run(
        ["hdiutil", "create", "-volname", "Mnemai", "-srcfolder", str(stage), "-ov", "-format", "UDZO", str(dmg)],
        check=True,
        capture_output=True,
    )
    shutil.rmtree(stage, ignore_errors=True)
    sha_file(dmg)
    return dmg


APP_ID = "io.github.pumpetee.mnema"  # the AppStream id: the catalogs know Mnemai by it
DESKTOP = """[Desktop Entry]
Type=Application
Name=Mnemai
Comment=Your memory for every AI
Exec=Mnemai
Icon=mnema
Categories=Office;Utility;
Terminal=false
StartupWMClass=Mnemai
"""


def appimagetool() -> Path | None:
    """The official AppImage builder, checked against the digest GitHub publishes for it."""
    import json
    import urllib.request

    arch = "aarch64" if platform.machine().lower() in ("arm64", "aarch64") else "x86_64"
    tool = ROOT / "build-package" / f"appimagetool-{arch}.AppImage"
    if tool.exists():
        return tool
    try:
        api = "https://api.github.com/repos/AppImage/appimagetool/releases/tags/continuous"
        rel = json.loads(
            urllib.request.urlopen(urllib.request.Request(api, headers={"User-Agent": "mnema"}), timeout=60).read()
        )
        asset = next(a for a in rel["assets"] if a["name"] == f"appimagetool-{arch}.AppImage")
        data = urllib.request.urlopen(asset["browser_download_url"], timeout=300).read()
        if asset.get("digest") and asset["digest"] != "sha256:" + hashlib.sha256(data).hexdigest():
            raise SystemExit("appimagetool: sha256 не совпал с опубликованным")
    except (OSError, StopIteration, KeyError) as e:
        say(f"AppImage не собран: нет appimagetool ({e})")
        return None
    tool.parent.mkdir(parents=True, exist_ok=True)
    tool.write_bytes(data)
    tool.chmod(0o755)
    return tool


def build_linux(skip_tests: bool) -> Path:
    import tarfile

    py = venv_python()
    if not (ROOT / "vendor" / "llama" / "llama-server").exists():
        raise SystemExit("нет движка локальной модели: python tools/fetch_vendor.py")
    if not skip_tests:
        run_tests(py)
    out = pyinstaller(py)
    folder = out / "Mnemai"
    smoke(folder, folder / "mnemai-cli")
    arch = "aarch64" if platform.machine().lower() in ("arm64", "aarch64") else "x86_64"
    (folder / "version.txt").write_text(version(), encoding="utf-8")
    tgz = out / f"Mnemai-{version()}-linux-{arch}.tar.gz"
    say("архив")
    with tarfile.open(tgz, "w:gz") as t:
        t.add(folder, arcname="Mnemai")
    sha_file(tgz)
    tool = appimagetool()
    if not tool:
        return tgz
    appdir = out / "Mnemai.AppDir"
    shutil.rmtree(appdir, ignore_errors=True)
    shutil.copytree(folder, appdir / "usr" / "lib" / "mnema", symlinks=True)
    (appdir / "AppRun").write_text(
        '#!/bin/sh\nHERE="$(dirname "$(readlink -f "$0")")"\nexec "$HERE/usr/lib/mnema/Mnemai" "$@"\n', encoding="utf-8"
    )
    (appdir / "AppRun").chmod(0o755)
    share = appdir / "usr" / "share"
    for d in (appdir, share / "applications"):
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{APP_ID}.desktop").write_text(DESKTOP, encoding="utf-8")
    shutil.copy2(ROOT / "packaging" / "mnema.png", appdir / "mnema.png")
    icons = share / "icons" / "hicolor" / "512x512" / "apps"
    icons.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "packaging" / "mnema.png", icons / "mnema.png")
    # the name, the description and the screenshots of the main window the catalogs show; this release's date
    meta = (ROOT / "packaging" / f"{APP_ID}.metainfo.xml").read_text(encoding="utf-8")
    meta = re.sub(
        r'<release version="[^"]*" date="[^"]*"/>',
        f'<release version="{version()}" date="{time.strftime("%Y-%m-%d")}"/>',
        meta,
    )
    (share / "metainfo").mkdir(parents=True, exist_ok=True)
    (share / "metainfo" / f"{APP_ID}.metainfo.xml").write_text(meta, encoding="utf-8")
    img = out / f"Mnemai-{version()}-{arch}.AppImage"  # AppImages are Linux only: the name doesn't say it again
    img.unlink(missing_ok=True)
    say("AppImage")
    # update information: AppImageUpdate and the like find the newest release on GitHub through the .zsync beside it
    update = f"gh-releases-zsync|Pumpetee|Mnemai|latest|Mnemai-*-{arch}.AppImage.zsync"
    r = subprocess.run(
        [str(tool), "--appimage-extract-and-run", "-u", update, str(appdir), str(img)],
        capture_output=True,
        text=True,
        env=dict(os.environ, ARCH=arch),
    )
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise SystemExit("AppImage не собрался")
    shutil.rmtree(appdir, ignore_errors=True)
    zs = img.name + ".zsync"  # appimagetool writes it into the folder it was started from, not next to the AppImage
    for where in (Path.cwd(), ROOT, appdir.parent):
        if (where / zs).exists() and where / zs != img.with_name(zs):
            shutil.move(str(where / zs), str(img.with_name(zs)))
            break
    if not img.with_name(img.name + ".zsync").exists():
        say("AppImage без .zsync: обновление через AppImageUpdate не заработает")
    sha_file(img)
    return img


def main() -> None:
    system = platform.system()
    skip = "--skip-tests" in sys.argv
    say(f"система: {system} {platform.machine()} · Mnemai {version()}")
    if system == "Windows":
        if platform.machine().lower() not in ("amd64", "x86_64"):
            raise SystemExit("нужна 64-битная Windows на x64")
        build_windows(skip)
    elif system == "Darwin":
        build_macos(skip)
    elif system == "Linux":
        build_linux(skip)
    else:
        raise SystemExit(f"{system}: не поддерживается")


if __name__ == "__main__":
    main()
