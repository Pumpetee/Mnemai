Lade die Datei für dein System herunter (alle Builds findest du unter [Releases](../../releases)):

| System | Datei | Vorgehen |
|---|---|---|
| Windows 10 und 11 | [`Mnemai-Setup.exe`](../../releases/latest/download/Mnemai-Setup.exe) | Ausführen. Es sind keine Administratorrechte nötig. Eine portable `.zip` gibt es ebenfalls. |
| macOS 11 und neuer | Apple Silicon: [`Mnemai-macos-arm64.dmg`](../../releases/latest/download/Mnemai-macos-arm64.dmg), Intel: [`Mnemai-macos-x64.dmg`](../../releases/latest/download/Mnemai-macos-x64.dmg) | Öffnen und Mnemai in den Ordner „Programme“ ziehen. |
| Linux x86-64 (Ubuntu 22.04 und neuer, Fedora, Debian …) | [`Mnemai-x86_64.AppImage`](../../releases/latest/download/Mnemai-x86_64.AppImage) | `chmod +x Mnemai-*.AppImage` und ausführen. Dasselbe Programm als Ordner: `.tar.gz`, darin `Mnemai` ausführen. |

Die Pakete sind noch nicht codesigniert, daher warnt jedes System einmalig:

- **Windows** SmartScreen meldet „Der Computer wurde durch Windows geschützt“. Klicke auf **Weitere Informationen → Trotzdem ausführen**.
- **macOS** meldet, dass der Entwickler nicht überprüft werden kann. Klicke in „Programme“ mit der rechten Maustaste auf Mnemai → **Öffnen**, oder öffne Systemeinstellungen → Datenschutz & Sicherheit → **Trotzdem öffnen**.
- **Linux** Das AppImage benötigt FUSE 2: `sudo apt install libfuse2` (unter Ubuntu 24.04: `libfuse2t64`). Oder verwende die `.tar.gz`.

Um eine Datei zu überprüfen, vergleiche ihren sha256-Wert mit der daneben liegenden `.sha256`-Datei: `certutil -hashfile <file> SHA256` unter Windows, `shasum -a 256 <file>` unter macOS, `sha256sum <file>` unter Linux.
