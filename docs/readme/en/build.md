Windows:

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python tools\fetch_vendor.py      # llama.cpp, Xray, WebView2 from their official releases, verified
.venv\Scripts\python -m mnema.desktop           # run the program
.venv\Scripts\python tools\package.py           # dist\Mnemai-Setup-*.exe and the portable zip
```

macOS and Linux:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python tools/fetch_vendor.py           # llama.cpp and Xray for this system, verified by sha256
.venv/bin/python -m mnema.desktop                # run the program
.venv/bin/python tools/package.py                # macOS: dist/Mnemai-*-macos-arm64.dmg
                                                 # Linux: dist/Mnemai-*-x86_64.AppImage and .tar.gz
```

Every push is tested on Windows, macOS and Linux; the three packages are built, started once with their window and kept as files of the run (`.github/workflows`).

The core needs only the Python standard library. It covers the vault, access rules, journal, MCP server and command line:

```bash
python -m mnema init ~/mnema --default
python -m mnema serve                    # http://127.0.0.1:7461
python -m mnema install claude-code      # shows the plan; add --apply
```
