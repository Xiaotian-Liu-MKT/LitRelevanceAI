import argparse
from typing import List, Optional

from .logging_config import get_default_logger


def _run_csv(_: argparse.Namespace) -> None:
    from . import csv_analyzer

    csv_analyzer.main()


def _run_abstract(args: argparse.Namespace) -> None:
    if getattr(args, "gui", False):
        # Launch the PyQt6 GUI application
        from .gui.main_window_qt import launch_gui

        launch_gui()
    else:
        from . import abstract_screener

        abstract_screener.main()


def _run_matrix(_: argparse.Namespace) -> None:
    from . import matrix_analyzer

    matrix_analyzer.main()


def main(argv: Optional[List[str]] = None) -> None:
    """Entry point for the ``litrx`` command line interface."""
    # Install logging and the sanitized exception hook as early as possible so
    # secrets in uncaught errors don't leak before subcommands run.
    get_default_logger()

    parser = argparse.ArgumentParser(prog="litrx", description="Literature analysis tools")
    subparsers = parser.add_subparsers(dest="command")

    csv_parser = subparsers.add_parser("csv", help="Analyze relevance from a Scopus CSV file")
    csv_parser.set_defaults(func=_run_csv)

    abstract_parser = subparsers.add_parser("abstract", help="Screen abstracts with optional GUI")
    abstract_parser.add_argument("--gui", action="store_true", help="Launch graphical interface")
    abstract_parser.set_defaults(func=_run_abstract)

    matrix_parser = subparsers.add_parser("matrix", help="Literature matrix analysis from PDFs")
    matrix_parser.set_defaults(func=_run_matrix)

    args = parser.parse_args(argv)
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":  # pragma: no cover
    main()
