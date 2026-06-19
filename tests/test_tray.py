import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, Signal          # noqa: E402
from PySide6.QtGui import QIcon                       # noqa: E402
from PySide6.QtWidgets import QApplication            # noqa: E402

from ecoworthy_bms.tray import SystemTray, render_soc_icon  # noqa: E402

_app = QApplication.instance() or QApplication([])


class _Win(QObject):
    connectToggled = Signal()


def test_render_soc_icon_variants():
    for soc in (None, 0, 62, 100):
        ic = render_soc_icon(soc)
        assert isinstance(ic, QIcon) and not ic.isNull()


def test_is_available_returns_bool():
    assert isinstance(SystemTray.is_available(), bool)


def test_notify_gate_off_is_noop():
    tray = SystemTray(_app, _Win(), render_soc_icon(None))
    tray.notifications_enabled = False
    tray.notify("title", "body")          # must not raise / must no-op when off
