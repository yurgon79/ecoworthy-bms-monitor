"""System-tray integration (M7): a live tray icon (SOC + state colour), context
menu, minimize/close-to-tray, and native notifications. Windows QoL.

`render_soc_icon` is pure (given a QApplication) and unit/preview-testable; the
tray itself needs a real desktop session, so `SystemTray.start()` is separate
and guarded by `is_available()`.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .config import BRAND_BLUE, CHARGE_GREEN, DISCHARGE_ORANGE, IDLE_GREY
from .model import PackState, Reading

_STATE_COLOR = {
    PackState.CHARGING: CHARGE_GREEN,
    PackState.FLOAT: "#0a8ac0",
    PackState.DISCHARGING: DISCHARGE_ORANGE,
    PackState.IDLE: IDLE_GREY,
    PackState.GRID_DOWN: "#c0392b",
    PackState.UNKNOWN: IDLE_GREY,
}


def render_soc_icon(soc: Optional[int], color: str = BRAND_BLUE) -> QIcon:
    """A 64×64 rounded badge: state colour + big SOC number (or '··' if unknown)."""
    pm = QPixmap(64, 64)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))
    p.drawRoundedRect(2, 2, 60, 60, 14, 14)
    p.setPen(QColor("white"))
    f = QFont(); f.setBold(True)
    f.setPointSize(30 if (soc is not None and soc < 100) else 22)
    p.setFont(f)
    p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter,
               "··" if soc is None else str(int(soc)))
    p.end()
    return QIcon(pm)


class SystemTray:
    def __init__(self, app: QApplication, window, fallback_icon: QIcon) -> None:
        self._app = app
        self._win = window
        self._fallback = fallback_icon
        self.notifications_enabled = True
        self._tray = QSystemTrayIcon(fallback_icon, app)
        self._tray.setToolTip("ECO-WORTHY BMS")
        menu = QMenu()
        self._act_show = QAction("Show / Hide", menu)
        self._act_show.triggered.connect(self.toggle_window)
        self._act_conn = QAction("Connect / Disconnect", menu)
        self._act_conn.triggered.connect(window.connectToggled.emit)
        self._act_quit = QAction("Quit", menu)
        self._act_quit.triggered.connect(self.quit)
        menu.addAction(self._act_show)
        menu.addAction(self._act_conn)
        menu.addSeparator()
        menu.addAction(self._act_quit)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_activated)

    @staticmethod
    def is_available() -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def start(self) -> None:
        self._tray.show()

    def _on_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self.toggle_window()

    def toggle_window(self) -> None:
        if self._win.isVisible():
            self._win.hide()
        else:
            self._win.showNormal()
            self._win.raise_()
            self._win.activateWindow()

    def update_reading(self, r: Reading, state: PackState) -> None:
        color = _STATE_COLOR.get(state, BRAND_BLUE)
        self._tray.setIcon(render_soc_icon(r.soc_pct, color))
        self._tray.setToolTip(
            f"ECO-WORTHY BMS — {r.soc_pct}% · {r.voltage_v:.2f} V · {state.value}")

    def notify(self, title: str, body: str, critical: bool = False) -> None:
        if not self.notifications_enabled:
            return
        icon = (QSystemTrayIcon.MessageIcon.Critical if critical
                else QSystemTrayIcon.MessageIcon.Information)
        self._tray.showMessage(title, body, icon, 8000)

    def quit(self) -> None:
        self._tray.hide()
        self._app.quit()
