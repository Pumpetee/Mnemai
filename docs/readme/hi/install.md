अपने सिस्टम के लिए फ़ाइल डाउनलोड करें (सभी बिल्ड [Releases](../../releases) में हैं):

| सिस्टम | फ़ाइल | कैसे |
|---|---|---|
| Windows 10 और 11 | [`Mnemai-Setup.exe`](../../releases/latest/download/Mnemai-Setup.exe) | इसे चलाएँ। एडमिनिस्ट्रेटर अधिकारों की आवश्यकता नहीं है। एक पोर्टेबल `.zip` भी उपलब्ध है। |
| macOS 11 और उसके बाद के संस्करण | Apple Silicon: [`Mnemai-macos-arm64.dmg`](../../releases/latest/download/Mnemai-macos-arm64.dmg), Intel: [`Mnemai-macos-x64.dmg`](../../releases/latest/download/Mnemai-macos-x64.dmg) | इसे खोलें और Mnemai को Applications में खींचकर डालें। |
| Linux x86-64 (Ubuntu 22.04 और उसके बाद के संस्करण, Fedora, Debian…) | [`Mnemai-x86_64.AppImage`](../../releases/latest/download/Mnemai-x86_64.AppImage) | `chmod +x Mnemai-*.AppImage` चलाएँ और फिर इसे चलाएँ। वही प्रोग्राम फ़ोल्डर के रूप में: `.tar.gz`, उसके अंदर `Mnemai` चलाएँ। |

पैकेज अभी कोड-साइन नहीं किए गए हैं, इसलिए हर सिस्टम एक बार चेतावनी देगा:

- **Windows** SmartScreen «Windows protected your PC» कहता है। **More info → Run anyway** पर क्लिक करें।
- **macOS** कहता है कि वह डेवलपर की जाँच नहीं कर सकता। Applications में Mnemai पर राइट-क्लिक करें → **Open**, या System Settings → Privacy & Security खोलें → **Open Anyway**।
- **Linux** AppImage के लिए FUSE 2 आवश्यक है: `sudo apt install libfuse2` (Ubuntu 24.04 पर: `libfuse2t64`)। या `.tar.gz` का उपयोग करें।

किसी फ़ाइल की जाँच करने के लिए, उसके sha256 की तुलना उसके साथ मौजूद `.sha256` फ़ाइल से करें: Windows पर `certutil -hashfile <file> SHA256`, macOS पर `shasum -a 256 <file>`, Linux पर `sha256sum <file>`।
