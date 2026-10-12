"""Entry point for the AppImage bundle: GUI with no arguments, CLI otherwise.

One PyInstaller binary instead of two — a second copy of the interpreter and
of the package would double the AppImage for no gain.
"""

import sys

from conveyr.cli import main as cli_main
from conveyr.gui import main as gui_main

if len(sys.argv) > 1:
    sys.exit(cli_main())
sys.exit(gui_main())