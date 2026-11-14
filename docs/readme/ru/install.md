Скачай файл для своей системы (все сборки — в [Releases](../../releases)):

| Система | Файл | Как поставить |
|---|---|---|
| Windows 10 и 11 | [`Mnemai-Setup.exe`](../../releases/latest/download/Mnemai-Setup.exe) | Запусти. Права администратора не нужны. Там же переносной `.zip`. |
| macOS 11 и новее | Apple Silicon: [`Mnemai-macos-arm64.dmg`](../../releases/latest/download/Mnemai-macos-arm64.dmg), Intel: [`Mnemai-macos-x64.dmg`](../../releases/latest/download/Mnemai-macos-x64.dmg) | Открой и перетащи Mnemai в «Программы». |
| Linux x86-64 (Ubuntu 22.04 и новее, Fedora, Debian…) | [`Mnemai-x86_64.AppImage`](../../releases/latest/download/Mnemai-x86_64.AppImage) | `chmod +x Mnemai-*.AppImage` и запусти. Та же программа папкой: `.tar.gz`, внутри запусти `Mnemai`. |

Пакеты пока без цифровой подписи, поэтому каждая система один раз предупредит:

- **Windows** покажет «Windows защитила ваш компьютер». Нажми **Подробнее → Выполнить в любом случае**.
- **macOS** скажет, что не может проверить разработчика. Нажми на Mnemai в «Программах» правой кнопкой → **Открыть** или открой Системные настройки → Конфиденциальность и безопасность → **Всё равно открыть**.
- **Linux**: для AppImage нужен FUSE 2 — `sudo apt install libfuse2` (на Ubuntu 24.04 — `libfuse2t64`). Или возьми `.tar.gz`.

Чтобы проверить файл, сравни его sha256 с файлом `.sha256` рядом: `certutil -hashfile <файл> SHA256` на Windows, `shasum -a 256 <файл>` на macOS, `sha256sum <файл>` на Linux.
