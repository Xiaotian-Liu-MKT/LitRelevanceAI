import argparse

from . import csv_analyzer, abstract_screener, matrix_analyzer


def main(argv: list[str] | None = None) -> None:
    """Entry point for the ``litrx`` command line interface."""
    parser = argparse.ArgumentParser(prog="litrx", description="Literature analysis tools")
    subparsers = parser.add_subparsers(dest="command")

    csv_parser = subparsers.add_parser("csv", help="Analyze relevance from a Scopus CSV file")
    csv_parser.set_defaults(func=lambda args: csv_analyzer.main())

    abstract_parser = subparsers.add_parser("abstract", help="Screen abstracts with optional GUI")
    abstract_parser.add_argument("--gui", action="store_true", help="Launch graphical interface")
    abstract_parser.set_defaults(
        func=lambda args: abstract_screener.run_gui() if args.gui else abstract_screener.main()
    )

    matrix_parser = subparsers.add_parser("matrix", help="Literature matrix analysis from PDFs")
    matrix_parser.set_defaults(func=lambda args: matrix_analyzer.main())

    args = parser.parse_args(argv)
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":  # pragma: no cover
    main()
