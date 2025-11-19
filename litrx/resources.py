"""Resource path helper to work in both dev and frozen (PyInstaller) builds."""

from __future__ import annotations

import sys
from pathlib import Path


def resource_path(*parts: str) -> Path:
    """Return absolute path to a bundled resource.

    When running from a PyInstaller build, resources live under the
    temporary `_MEIPASS` directory. In development, resources live at the
    repository root alongside `configs/`, `questions_config.json`, etc.
    """
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base.joinpath(*parts)

