Windows:

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python tools\fetch_vendor.py      # llama.cpp, Xray, WebView2 from their official releases, verified
.venv\Scripts\python -m mnema.desktop           # run the program
.venv\Scripts\python tools\package.py           # dist\Mnemai-Setup-*.exe and the portable zip
```

macOS und Linux:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python tools/fetch_vendor.py           # llama.cpp and Xray for this system, verified by sha256
.venv/bin/python -m mnema.desktop                # run the program
.venv/bin/python tools/package.py                # macOS: dist/Mnemai-*-macos-arm64.dmg
                                                 # Linux: dist/Mnemai-*-x86_64.AppImage and .tar.gz
```

Jeder Push wird unter Windows, macOS und Linux getestet; die drei Pakete werden gebaut, einmal mit ihrem Fenster gestartet und als Dateien des Laufs aufbewahrt (`.github/workflows`).

Der Kern benötigt nur die Python-Standardbibliothek. Er umfasst den Vault, die Zugriffsregeln, das Journal, den MCP-Server und die Kommandozeile:

```bash
python -m mnema init ~/mnema --default
python -m mnema serve                    # http://127.0.0.1:7461
python -m mnema install claude-code      # shows the plan; add --apply
