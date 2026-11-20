"""Первый запуск: создать, открыть или взять демо-память.

Единая логика для обоих входов ViewModel: pywebview-слотов (desktop.Api) и HTTP-маршрутов роутера
(POST /api/app/create|demo|open_existing, GET /api/app/default_path). Функции возвращают
(err, vault): err — (текст для пользователя, HTTP-код) или None, vault — открытая память или None.
Слоты показывают только текст; маршруты оборачивают пару в единую ошибку роутера.
"""

from __future__ import annotations

from pathlib import Path

from .memory import init_vault
from .vault import Vault


def default_path() -> str:
    from . import upgrade

    return str(upgrade.free_memory_path())


def open_existing(path: str, lang: str = "en") -> tuple[tuple[str, int] | None, Vault | None]:
    """«Указать, где она»: an existing memory folder opens as is; anything else says why not."""
    try:
        v = Vault(Path(path).expanduser())
        if not v.root.exists():
            return ("Этой папки нет. Проверь, подключён ли диск." if lang == "ru" else "No such folder.", 400), None
        if not v.exists():
            return (
                "Здесь нет памяти Mnemai: нет файла «70 Memory/Profile.md». Выбери папку, где лежат «70 Memory» и «.mnema»."
                if lang == "ru"
                else "There is no Mnemai memory here: «70 Memory/Profile.md» is missing.",
                400,
            ), None
        return None, v
    except Exception as e:
        return (f"Не получилось: {e}", 500), None


def _prefs(v: Vault, prefs: dict | None):
    if not prefs:
        return
    from .agent import profile as P

    patch = {
        "lang": prefs.get("lang") or "en",
        "gender": prefs.get("gender") or "",
        "owner_name": (prefs.get("name") or "")[:60],
        "ui_theme": prefs.get("theme") if prefs.get("theme") in ("light", "dark", "system") else "",
    }
    if prefs.get("address") in ("ty", "vy"):
        patch["simple"] = {"address": prefs["address"]}
    P.save(v, patch)


def _proxy(v: Vault, url: str, password: str):
    if url:
        from . import net

        net.save(v, url, password or "")


def _path_checks(p: Path) -> str | None:
    """Ошибки пути для новой памяти (или None): полный путь, живой диск, без запрещённых Windows-знаков."""
    from . import osapi as OS

    if not p.is_absolute():
        example = "C:\\Users\\Имя\\Mnemai" if OS.IS_WIN else "~/Mnemai"
        return f"Нужен полный путь к папке, например {example} — или нажми «Выбрать…»."
    if p.drive and not Path(p.drive + "\\").exists():
        return f"Диска {p.drive} нет на компьютере. Выбери другую папку."
    bad = set('<>"|?*') & set(str(p)[len(p.drive) :]) if OS.IS_WIN else set()
    if bad:
        return "В пути есть знаки, которые Windows не разрешает в именах папок: " + " ".join(sorted(bad))
    if OS.IS_WIN and any(
        x.upper().split(".")[0]
        in (
            "CON",
            "PRN",
            "AUX",
            "NUL",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10)),
        )
        for x in p.parts[1:]
    ):
        return "Такое имя папки Windows не разрешает (CON, NUL, COM1…). Выбери другое."
    return None


def create(
    path: str, proxy: str = "", password: str = "", prefs: dict | None = None
) -> tuple[tuple[str, int] | None, Vault | None]:
    if not (path or "").strip():
        return ("Укажи папку для памяти — или нажми «Выбрать…».", 400), None
    try:
        p = Path(path.strip()).expanduser()
        err = _path_checks(p)
        if err:
            return (err, 400), None
        from . import upgrade

        if upgrade.old_layout(p):  # the first build's memory: left as it is, new one beside it
            p = p.with_name(p.name + " Memory")
        if upgrade.is_app_dir(p) or any(upgrade.is_app_dir(x) for x in p.parents):
            p = upgrade.free_memory_path()  # never inside a program folder: an update replaces it
        if p.exists() and any(p.iterdir()) and not Vault(p).exists() and not (p / ".mnema").exists():
            p = p / "Mnemai"  # never spill memory files into a non-empty folder
        v = Vault(p)
        fresh = not v.exists()
        init_vault(v)
        _proxy(v, proxy, password)
        _prefs(v, prefs)
        if fresh:  # a new memory starts switched off: the tour offers to turn it on
            from .agent import profile as P

            P.save(v, {"memory_on": False})
        return None, v
    except PermissionError:
        return ("Нет прав записывать в эту папку. Выбери другую — например, в «Документах».", 500), None
    except OSError as e:
        return (f"Не получилось создать папку: {e.strerror or e}. Выбери другую.", 500), None
    except Exception as e:
        return (f"Не получилось: {e}", 500), None


def demo(proxy: str = "", password: str = "", prefs: dict | None = None) -> tuple[tuple[str, int] | None, Vault | None]:
    try:
        from .cli import HOME
        from .demo import make_demo

        p = HOME / "demo"
        v = Vault(p)
        if not v.exists():
            make_demo(v)
        _proxy(v, proxy, password)
        _prefs(v, prefs)
        return None, v
    except Exception as e:
        return (f"Не получилось: {e}", 500), None
