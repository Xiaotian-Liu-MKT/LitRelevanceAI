"""Package entry point for `python -m litrx`."""

import argparse
from typing import List, Optional

from . import cli


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="LitRx tools")
    parser.add_argument("--gui", action="store_true", help="Launch graphical interface")
    args, remaining = parser.parse_known_args(argv)
    if args.gui:
        # Import Qt GUI lazily
        from .gui.main_window_qt import launch_gui

        launch_gui()
    else:
        # Delegate to CLI with remaining arguments
        cli.main(remaining)


if __name__ == "__main__":  # pragma: no cover
    main()
