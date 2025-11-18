"""Utilities to keep Tkinter stable across macOS releases."""

from __future__ import annotations

import os
import platform
from typing import Final

# Guard so we only touch the environment once per process.
_ENV_FORCED: Final[str] = "0"
_HAS_PATCHED = False


def ensure_native_macos_version() -> None:
    """Force Tk to read the host macOS version instead of the legacy shim."""
    global _HAS_PATCHED
    if _HAS_PATCHED:
        return
    if platform.system() != "Darwin":
        return

    compat_value = os.environ.get("SYSTEM_VERSION_COMPAT")
    if compat_value == _ENV_FORCED:
        _HAS_PATCHED = True
        return

    # Tk bases its runtime checks on this environment variable. When it is left
    # at "1", modern macOS releases such as Sequoia (15) are reported as the
    # legacy "10.16", which triggers crashes. Setting it to "0" forces Tk to
    # see the real version number and prevents the "macOS 26…have instead 16"
    # abort.
    os.environ["SYSTEM_VERSION_COMPAT"] = _ENV_FORCED
    _HAS_PATCHED = True


# Apply the fix automatically when the helper is imported so every GUI entry
# point (CLI, GUI launcher, notebooks) benefits without needing to call the
# function manually.
ensure_native_macos_version()
