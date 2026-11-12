Download the file for your system (every version with its number is in [Releases](../../releases)):

| System | File | How |
|---|---|---|
| Windows 10 and 11 | [`Mnemai-Setup.exe`](../../releases/latest/download/Mnemai-Setup.exe) | Run it. No administrator rights needed. A portable `.zip` is there as well. |
| macOS 11 and newer | Apple Silicon: [`Mnemai-macos-arm64.dmg`](../../releases/latest/download/Mnemai-macos-arm64.dmg), Intel: [`Mnemai-macos-x64.dmg`](../../releases/latest/download/Mnemai-macos-x64.dmg) | Open it and drag Mnemai to Applications. |
| Linux x86-64 (Ubuntu 22.04 and newer, Fedora, Debian…) | [`Mnemai-x86_64.AppImage`](../../releases/latest/download/Mnemai-x86_64.AppImage) | `chmod +x Mnemai-*.AppImage` and run it. The same program as a folder: `.tar.gz`, run `Mnemai` inside. |

Installed Windows copies download verified stable releases in the background and
update silently after you choose Exit, then return to the tray. See
[background updates](docs/auto-updates.md) for details and how to turn them off.

The packages are not code-signed yet, so each system warns once:

- **Windows** SmartScreen says «Windows protected your PC». Click **More info → Run anyway**.
- **macOS** says it can't check the developer. Right-click Mnemai in Applications → **Open**, or open System Settings → Privacy & Security → **Open Anyway**.
- **Linux** AppImage needs FUSE 2: `sudo apt install libfuse2` (on Ubuntu 24.04: `libfuse2t64`). Or use the `.tar.gz`.

To check a file, compare its sha256 with the `.sha256` file beside it: `certutil -hashfile <file> SHA256` on Windows, `shasum -a 256 <file>` on macOS, `sha256sum <file>` on Linux.
