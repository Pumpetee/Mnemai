下载适用于你系统的文件(所有构建都在 [Releases](../../releases) 中):

| 系统 | 文件 | 方法 |
|---|---|---|
| Windows 10 和 11 | [`Mnemai-Setup.exe`](../../releases/latest/download/Mnemai-Setup.exe) | 直接运行即可,无需管理员权限。同时也提供便携版 `.zip`。 |
| macOS 11 及更高版本 | Apple Silicon:[`Mnemai-macos-arm64.dmg`](../../releases/latest/download/Mnemai-macos-arm64.dmg),Intel:[`Mnemai-macos-x64.dmg`](../../releases/latest/download/Mnemai-macos-x64.dmg) | 打开后将 Mnemai 拖入“应用程序”文件夹。 |
| Linux x86-64(Ubuntu 22.04 及更高版本、Fedora、Debian……) | [`Mnemai-x86_64.AppImage`](../../releases/latest/download/Mnemai-x86_64.AppImage) | 执行 `chmod +x Mnemai-*.AppImage` 后运行。同一程序的文件夹版本:`.tar.gz`,运行其中的 `Mnemai` 即可。 |

这些安装包尚未进行代码签名,因此每个系统都会提示一次警告:

- **Windows** 的 SmartScreen 会显示“Windows 已保护你的电脑”。点击 **更多信息 → 仍要运行**。
- **macOS** 会提示无法验证开发者。在“应用程序”中右键点击 Mnemai → **打开**,或打开“系统设置” → “隐私与安全性” → **仍要打开**。
- **Linux** 的 AppImage 需要 FUSE 2:`sudo apt install libfuse2`(Ubuntu 24.04 上为 `libfuse2t64`)。或者使用 `.tar.gz`。

要校验文件,请将其 sha256 与旁边的 `.sha256` 文件进行比对:Windows 上使用 `certutil -hashfile <file> SHA256`,macOS 上使用 `shasum -a 256 <file>`,Linux 上使用 `sha256sum <file>`。
