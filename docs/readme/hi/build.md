Windows:

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python tools\fetch_vendor.py      # llama.cpp, Xray, WebView2 from their official releases, verified
.venv\Scripts\python -m mnema.desktop           # run the program
.venv\Scripts\python tools\package.py           # dist\Mnemai-Setup-*.exe and the portable zip
```

macOS और Linux:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python tools/fetch_vendor.py           # llama.cpp and Xray for this system, verified by sha256
.venv/bin/python -m mnema.desktop                # run the program
.venv/bin/python tools/package.py                # macOS: dist/Mnemai-*-macos-arm64.dmg
                                                 # Linux: dist/Mnemai-*-x86_64.AppImage and .tar.gz
```

हर push का परीक्षण Windows, macOS और Linux पर किया जाता है; तीनों पैकेज बनाए जाते हैं, एक बार उनकी विंडो के साथ चलाए जाते हैं और रन की फ़ाइलों के रूप में सहेजे जाते हैं (`.github/workflows`)।

कोर को केवल Python की मानक लाइब्रेरी चाहिए। इसमें वॉल्ट, एक्सेस नियम, जर्नल, MCP सर्वर और कमांड लाइन शामिल हैं:

```bash
python -m mnema init ~/mnema --default
python -m mnema serve                    # http://127.0.0.1:7461
python -m mnema install claude-code      # shows the plan; add --apply
