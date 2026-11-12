from mnema.updater import hold_cli_install_lock

_install_lock = hold_cli_install_lock()

from mnema.cli import main

main()
