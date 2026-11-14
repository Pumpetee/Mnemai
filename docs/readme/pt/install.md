Baixe o arquivo para o seu sistema (todas as compilações estão em [Releases](../../releases)):

| Sistema | Arquivo | Como |
|---|---|---|
| Windows 10 e 11 | [`Mnemai-Setup.exe`](../../releases/latest/download/Mnemai-Setup.exe) | Execute-o. Não é necessário ter direitos de administrador. Um `.zip` portátil também está disponível. |
| macOS 11 e mais recente | Apple Silicon: [`Mnemai-macos-arm64.dmg`](../../releases/latest/download/Mnemai-macos-arm64.dmg), Intel: [`Mnemai-macos-x64.dmg`](../../releases/latest/download/Mnemai-macos-x64.dmg) | Abra-o e arraste o Mnemai para Aplicativos. |
| Linux x86-64 (Ubuntu 22.04 e mais recente, Fedora, Debian…) | [`Mnemai-x86_64.AppImage`](../../releases/latest/download/Mnemai-x86_64.AppImage) | `chmod +x Mnemai-*.AppImage` e execute-o. O mesmo programa em formato de pasta: `.tar.gz`, execute `Mnemai` dentro dela. |

Os pacotes ainda não são assinados digitalmente, então cada sistema exibe um aviso uma vez:

- **Windows**: o SmartScreen diz «O Windows protegeu seu PC». Clique em **Mais informações → Executar assim mesmo**.
- **macOS**: informa que não é possível verificar o desenvolvedor. Clique com o botão direito no Mnemai em Aplicativos → **Abrir**, ou abra Ajustes do Sistema → Privacidade e Segurança → **Abrir Mesmo Assim**.
- **Linux**: o AppImage precisa do FUSE 2: `sudo apt install libfuse2` (no Ubuntu 24.04: `libfuse2t64`). Ou use o `.tar.gz`.

Para verificar um arquivo, compare o sha256 dele com o arquivo `.sha256` que está ao lado: `certutil -hashfile <arquivo> SHA256` no Windows, `shasum -a 256 <arquivo>` no macOS, `sha256sum <arquivo>` no Linux.
