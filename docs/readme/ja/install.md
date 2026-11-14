お使いのシステム用のファイルをダウンロードしてください（すべてのビルドは [Releases](../../releases) にあります）:

| システム | ファイル | 方法 |
|---|---|---|
| Windows 10 および 11 | [`Mnemai-Setup.exe`](../../releases/latest/download/Mnemai-Setup.exe) | 実行してください。管理者権限は不要です。ポータブル版の `.zip` も用意されています。 |
| macOS 11 以降 | Apple Silicon: [`Mnemai-macos-arm64.dmg`](../../releases/latest/download/Mnemai-macos-arm64.dmg)、Intel: [`Mnemai-macos-x64.dmg`](../../releases/latest/download/Mnemai-macos-x64.dmg) | 開いて、Mnemai を Applications にドラッグしてください。 |
| Linux x86-64（Ubuntu 22.04 以降、Fedora、Debian など） | [`Mnemai-x86_64.AppImage`](../../releases/latest/download/Mnemai-x86_64.AppImage) | `chmod +x Mnemai-*.AppImage` を実行してから起動してください。同じプログラムをフォルダ形式にした `.tar.gz` もあり、中の `Mnemai` を実行します。 |

パッケージにはまだコード署名がないため、各システムで初回に一度だけ警告が表示されます:

- **Windows** SmartScreen に「Windows によって PC が保護されました」と表示されます。**詳細情報 → 実行** をクリックしてください。
- **macOS** 開発元を確認できないと表示されます。Applications の Mnemai を右クリックして **開く** を選ぶか、システム設定 → プライバシーとセキュリティ → **このまま開く** をクリックしてください。
- **Linux** AppImage には FUSE 2 が必要です: `sudo apt install libfuse2`（Ubuntu 24.04 では `libfuse2t64`）。または `.tar.gz` を使用してください。

ファイルを検証するには、その sha256 を隣にある `.sha256` ファイルと比較してください: Windows では `certutil -hashfile <file> SHA256`、macOS では `shasum -a 256 <file>`、Linux では `sha256sum <file>`。
