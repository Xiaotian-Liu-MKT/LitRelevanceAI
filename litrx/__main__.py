"""Package entry point for `python -m litrx`."""

import argparse
from typing import List, Optional

from . import cli
from .logging_config import get_default_logger


def main(argv: Optional[List[str]] = None) -> None:
    # Configure logging (and install the sanitized exception hook) before
    # parsing CLI arguments so GUI and CLI paths are both protected.
    get_default_logger()

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
