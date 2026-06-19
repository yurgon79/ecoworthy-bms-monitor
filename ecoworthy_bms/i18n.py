"""Internationalization loader (v0.2 scaffold).

The UI strings are wrapped in Qt's tr()/translate(); with no catalog loaded
they render as the English source. Drop `app_<locale>.qm` files into
`translations/` and they load automatically for that system locale.
See translations/README.md for the contributor workflow.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QLocale, QTranslator


def install_translator(app, locale: Optional[str] = None) -> Optional[str]:
    """Install a translation for `locale` (default: system). Returns the loaded
    locale tag, or None if no catalog matched (English source is used)."""
    loc = locale or QLocale.system().name()          # e.g. "de_DE"
    tdir = Path(__file__).resolve().parent / "translations"
    tr = QTranslator(app)
    for cand in (loc, loc.split("_")[0]):
        qm = tdir / f"app_{cand}.qm"
        if qm.exists() and tr.load(str(qm)):
            app.installTranslator(tr)
            return cand
    return None
