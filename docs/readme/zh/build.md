Windows：

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python tools\fetch_vendor.py      # llama.cpp、Xray、WebView2，均来自官方发布并经过校验
.venv\Scripts\python -m mnema.desktop           # 运行程序
.venv\Scripts\python tools\package.py           # dist\Mnemai-Setup-*.exe 以及便携版 zip
```

macOS 和 Linux：

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python tools/fetch_vendor.py           # 适用于当前系统的 llama.cpp 和 Xray，经 sha256 校验
.venv/bin/python -m mnema.desktop                # 运行程序
.venv/bin/python tools/package.py                # macOS: dist/Mnemai-*-macos-arm64.dmg
                                                 # Linux: dist/Mnemai-*-x86_64.AppImage 以及 .tar.gz
```

每次推送都会在 Windows、macOS 和 Linux 上进行测试；三个安装包都会被构建，并带窗口启动一次，且作为本次运行的文件保留下来（`.github/workflows`）。

核心部分只需要 Python 标准库。它涵盖保险库（vault）、访问规则、日志、MCP 服务器和命令行：

```bash
python -m mnema init ~/mnema --default
python -m mnema serve                    # http://127.0.0.1:7461
python -m mnema install claude-code      # shows the plan; add --apply
