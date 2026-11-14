Windows:

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python tools\fetch_vendor.py      # llama.cpp, Xray, WebView2 dos seus lançamentos oficiais, verificados
.venv\Scripts\python -m mnema.desktop           # executa o programa
.venv\Scripts\python tools\package.py           # dist\Mnemai-Setup-*.exe e o zip portátil
```

macOS e Linux:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python tools/fetch_vendor.py           # llama.cpp e Xray para este sistema, verificados por sha256
.venv/bin/python -m mnema.desktop                # executa o programa
.venv/bin/python tools/package.py                # macOS: dist/Mnemai-*-macos-arm64.dmg
                                                 # Linux: dist/Mnemai-*-x86_64.AppImage e .tar.gz
```

Cada push é testado no Windows, macOS e Linux; os três pacotes são compilados, iniciados uma vez com sua janela e mantidos como arquivos da execução (`.github/workflows`).

O núcleo precisa apenas da biblioteca padrão do Python. Ele cobre o cofre, as regras de acesso, o diário, o servidor MCP e a linha de comando:

```bash
python -m mnema init ~/mnema --default
python -m mnema serve                    # http://127.0.0.1:7461
python -m mnema install claude-code      # mostra o plano; adicione --apply
