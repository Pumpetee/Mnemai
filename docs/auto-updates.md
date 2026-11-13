# Background updates on Windows

The installed Windows desktop app checks the latest published stable release of
`Pumpetee/Mnemai` 30 seconds after startup, then every six hours. Drafts, prereleases,
older versions and builds without a matching versioned Windows installer are ignored.
No GitHub account or token is needed.
Network requests follow the proxy selected in Mnemai, including the explicit
direct-connection setting.

The installer downloads into `~/.mnema/updates` (or `MNEMA_HOME/updates`). Its size
and SHA-256 must match the official GitHub release asset. If GitHub does not provide
an asset digest, the versioned `.exe.sha256` published by `tools/package.py` is used.
Requests and redirects are restricted to HTTPS on GitHub's download hosts. These
checks detect corruption; they do not protect against a compromised upstream
GitHub account. Release binaries are not currently code-signed.

Downloading does not close a window, interrupt a chat or stop a recording. When the
owner normally exits Mnemai, a hidden helper waits for that process to finish,
rechecks the hash, and runs the existing per-user installer with `/VERYSILENT`,
`/SUPPRESSMSGBOXES`, `/NORESTART` and `/AUTOUPDATE=1`. This mode replaces the same
installation without scanning/deleting other copies or migrating memory/settings.
On success, Mnemai starts hidden in the tray. Closing to the tray is not an exit;
the staged update waits until the owner chooses Exit.
If another desktop copy or a bundled MCP/CLI helper is still running, installation
is deferred. Exit the memory connection in Claude/Cursor before the next normal
Mnemai exit to let the update proceed; the updater never kills those helpers.

An unavailable GitHub API, incomplete release, failed download or checksum mismatch
leaves the current program running. Installation failures do not launch the new
program; inspect `~/.mnema/updates/update-install.log`. Inno Setup's existing file
replacement is used; there is no transactional rollback of a failed installation.
An interrupted installation may require rerunning the official installer manually.

To disable background updates, set `"auto_update": false` in `~/.mnema/config.json`
while Mnemai is closed, or launch with `MNEMA_NO_UPDATE=1`. This is checked again
before handing off installation. Source runs, portable Windows copies, macOS and
Linux do not self-update through this mechanism. Existing AppImage update metadata
continues to work independently.

Maintainers: publish the versioned `Mnemai-Setup-X.Y.Z.exe` and its checksum from
the normal build workflow, then publish the draft release. This implementation
must first reach users in a manually installed release; it cannot retrofit old
installed binaries. The next newer published release can then update automatically.
