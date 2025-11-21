"""Convenience script to launch the LitRx graphical interface.

Run:
    python run_gui.py

The script checks for required packages and installs them if missing.
Now uses PyQt6 for a modern UI experience.
"""

import importlib
import os
import subprocess
import sys

from litrx.logging_config import get_default_logger

DEPENDENCIES = {
    "pandas": "pandas",
    "openai": "openai",
    "tqdm": "tqdm",
    "openpyxl": "openpyxl",
    "pyyaml": "yaml",
    "pypdf": "pypdf",
    "PyQt6": "PyQt6.QtWidgets",
}


def ensure_dependencies() -> None:
    """Install required packages if they are missing."""
    missing = []
    for package, module in DEPENDENCIES.items():
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(package)
    if missing:
        print("Installing missing packages:", ", ".join(missing))
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", *missing])


def main() -> None:
    ensure_dependencies()
    # Set up logging early so GUI exceptions are sanitized
    get_default_logger()
    from litrx.gui.main_window_qt import launch_gui

    launch_gui()


if __name__ == "__main__":
    main()
