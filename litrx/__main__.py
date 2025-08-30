"""Package entry point for `python -m litrx`."""
from __future__ import annotations

import argparse
import sys

from . import cli
from .gui.main_window import launch_gui


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="LitRx tools")
    parser.add_argument("--gui", action="store_true", help="Launch graphical interface")
    args, remaining = parser.parse_known_args(argv)
    if args.gui:
        launch_gui()
    else:
        # Delegate to CLI with remaining arguments
        cli.main(remaining)


if __name__ == "__main__":  # pragma: no cover
    main()
