Descarga el archivo para tu sistema (todas las compilaciones están en [Releases](../../releases)):

| Sistema | Archivo | Cómo |
|---|---|---|
| Windows 10 y 11 | [`Mnemai-Setup.exe`](../../releases/latest/download/Mnemai-Setup.exe) | Ejecútalo. No se necesitan derechos de administrador. También hay un `.zip` portable. |
| macOS 11 y posterior | Apple Silicon: [`Mnemai-macos-arm64.dmg`](../../releases/latest/download/Mnemai-macos-arm64.dmg), Intel: [`Mnemai-macos-x64.dmg`](../../releases/latest/download/Mnemai-macos-x64.dmg) | Ábrelo y arrastra Mnemai a Aplicaciones. |
| Linux x86-64 (Ubuntu 22.04 y posterior, Fedora, Debian…) | [`Mnemai-x86_64.AppImage`](../../releases/latest/download/Mnemai-x86_64.AppImage) | `chmod +x Mnemai-*.AppImage` y ejecútalo. El mismo programa como carpeta: `.tar.gz`, ejecuta `Mnemai` dentro. |

Los paquetes todavía no están firmados con código, así que cada sistema muestra una advertencia la primera vez:

- **Windows**: SmartScreen dice «Windows protegió su PC». Haz clic en **Más información → Ejecutar de todas formas**.
- **macOS**: dice que no puede comprobar el desarrollador. Haz clic derecho en Mnemai en Aplicaciones → **Abrir**, o abre Ajustes del Sistema → Privacidad y seguridad → **Abrir de todos modos**.
- **Linux**: el AppImage necesita FUSE 2: `sudo apt install libfuse2` (en Ubuntu 24.04: `libfuse2t64`). O usa el `.tar.gz`.

Para comprobar un archivo, compara su sha256 con el archivo `.sha256` que está junto a él: `certutil -hashfile <file> SHA256` en Windows, `shasum -a 256 <file>` en macOS, `sha256sum <file>` en Linux.
