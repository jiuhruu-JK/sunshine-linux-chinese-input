"""Register Dockle's first-party Sphinx theme."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dockle import __version__

_PACKAGE_ROOT = Path(__file__).resolve().parent
THEME_DIRECTORY = _PACKAGE_ROOT / "sphinx" / "themes" / "dockle"


def setup(app: Any) -> dict[str, Any]:
    """Register the theme and its shared static assets with Sphinx."""

    app.add_html_theme("dockle", THEME_DIRECTORY)
    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
