Windows :

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python tools\fetch_vendor.py      # llama.cpp, Xray, WebView2 depuis leurs versions officielles, vérifiés
.venv\Scripts\python -m mnema.desktop           # lancer le programme
.venv\Scripts\python tools\package.py           # dist\Mnemai-Setup-*.exe et le zip portable
```

macOS et Linux :

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python tools/fetch_vendor.py           # llama.cpp et Xray pour ce système, vérifiés par sha256
.venv/bin/python -m mnema.desktop                # lancer le programme
.venv/bin/python tools/package.py                # macOS : dist/Mnemai-*-macos-arm64.dmg
                                                 # Linux : dist/Mnemai-*-x86_64.AppImage et .tar.gz
```

Chaque push est testé sur Windows, macOS et Linux ; les trois paquets sont construits, démarrés une fois avec leur fenêtre et conservés sous forme de fichiers de l'exécution (`.github/workflows`).

Le cœur n'a besoin que de la bibliothèque standard de Python. Il couvre le coffre (vault), les règles d'accès, le journal, le serveur MCP et la ligne de commande :

```bash
python -m mnema init ~/mnema --default
python -m mnema serve                    # http://127.0.0.1:7461
python -m mnema install claude-code      # affiche le plan ; ajouter --apply
