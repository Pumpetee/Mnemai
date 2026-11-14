Windows:

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python tools\fetch_vendor.py      # llama.cpp, Xray, WebView2 с официальных релизов, с проверкой
.venv\Scripts\python -m mnema.desktop           # запустить программу
.venv\Scripts\python tools\package.py           # dist\Mnemai-Setup-*.exe и переносной архив
```

macOS и Linux:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python tools/fetch_vendor.py           # llama.cpp и Xray для этой системы, с проверкой sha256
.venv/bin/python -m mnema.desktop                # запустить программу
.venv/bin/python tools/package.py                # macOS: dist/Mnemai-*-macos-arm64.dmg
                                                 # Linux: dist/Mnemai-*-x86_64.AppImage и .tar.gz
```

Каждый push проверяется на Windows, macOS и Linux: собираются три пакета, каждый один раз запускается с окном и остаётся файлами прогона (`.github/workflows`).

Ядру нужна только стандартная библиотека Python. Ядро — это папка памяти, права ИИ, журнал, MCP-сервер и командная строка:

```bash
python -m mnema init ~/mnema --default
python -m mnema serve                    # http://127.0.0.1:7461
python -m mnema install claude-code      # покажет план; добавь --apply
```
