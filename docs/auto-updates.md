# Updates

Every copy of Mnemai checks the latest published stable release of
`Pumpetee/Mnemai` a little after startup, then every six hours: drafts, prereleases,
older versions and builds without a file for this system are ignored. No GitHub
account or token is needed, and nothing is downloaded behind the owner's back on
macOS, Linux or a source run.

When a newer release exists, a small **Update** pill appears next to the gear with
the new version number; the gear menu also has the current version and a manual
«Check» button. The download starts only when the owner presses Update. Reopening
the notice is enough after pressing «Later»: the reminder for that version stays
quiet until the next release, and the gear's «Check» always asks again.

**Windows (installed copy).** The installed app also stages the verified installer in
the background and installs it after a normal exit, without a button.

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

**macOS.** The button downloads the `.dmg` for this Mac's architecture and opens it:
the owner drags Mnemai into Applications, as with a manual install (the app is not
code-signed).

**Linux.** The button downloads the AppImage for this architecture and, when Mnemai
itself runs from an AppImage, replaces that file and restarts the app. A folder
install (`.tar.gz`) or a source run never modifies itself: the downloaded file is
shown in its folder and the release page is offered.

**Portable Windows copy.** The button downloads the installer and shows it; running
it installs the per-user copy.

To disable the checks, set `"auto_update": false` in `~/.mnema/config.json` while
Mnemai is closed, or launch with `MNEMA_NO_UPDATE=1`. This is checked again before
handing off an installation. Existing AppImage update metadata continues to work
independently.

Maintainers: push a `vX.Y.Z` tag — the build workflow produces the versioned
packages and publishes the release automatically, with GitHub's generated notes.
The in-app Update button must first reach users in a manually installed release (or
through the silent Windows path); it cannot retrofit a copy that predates it. Every
newer published release can then update automatically.
