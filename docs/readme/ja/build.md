Windows:

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python tools\fetch_vendor.py      # llama.cpp, Xray, WebView2 を公式リリースから取得し、検証します
.venv\Scripts\python -m mnema.desktop           # プログラムを実行
.venv\Scripts\python tools\package.py           # dist\Mnemai-Setup-*.exe とポータブル版 zip
```

macOS と Linux:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python tools/fetch_vendor.py           # お使いのシステム向けの llama.cpp と Xray を取得し、sha256 で検証します
.venv/bin/python -m mnema.desktop                # プログラムを実行
.venv/bin/python tools/package.py                # macOS: dist/Mnemai-*-macos-arm64.dmg
                                                 # Linux: dist/Mnemai-*-x86_64.AppImage と .tar.gz
```

プッシュのたびに Windows、macOS、Linux でテストが実行されます。3 つのパッケージがビルドされ、ウィンドウ付きで一度起動され、その実行結果のファイルとして保存されます (`.github/workflows`)。

コアに必要なのは Python 標準ライブラリだけです。vault、アクセスルール、ジャーナル、MCP サーバー、コマンドラインをカバーしています。

```bash
python -m mnema init ~/mnema --default
python -m mnema serve                    # http://127.0.0.1:7461
python -m mnema install claude-code      # 計画を表示します。--apply を付けると適用されます
