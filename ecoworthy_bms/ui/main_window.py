"""Application shell: sidebar nav + stacked pages + battery switcher, and the
coordinator that fans BLE readings out to every page, logs history, turns
readings/status into Messages, drives the fail-safe safety state, feeds the
system tray, and maintains the bank view. (Concurrent multi-pack polling is
deferred; the bank shows the active pack now and is ready for the rest.)
"""
from __future__ import annotations

import asyncio
import time
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

from .. import __version__
from ..alerts import Alert, AlertEngine, Category, Severity
from ..autostart import apply_autostart
from ..config import AppConfig
from ..history import HistoryLog
from ..model import Reading
from ..profiles import profiles_from_config
from ..safety.actions import SafetyActions
from ..safety.failsafe import FailsafeMonitor, Safety
from .bank import BankPage
from .cells import CellsPage
from .history_page import HistoryPage
from .messages import MessagesPage
from .monitor import MonitorPage
from .settings import SettingsPage

_NAV = ["Monitor", "Bank", "Cells", "History", "Messages", "Settings"]


class MainWindow(QWidget):
    connectToggled = Signal()
    readerReconfigured = Signal(str, float)  # mac, poll_sec (restart reader)
    alpacaReconfigured = Signal(bool, int)   # enabled, port (restart Alpaca server)

    def __init__(self, cfg: AppConfig, log: Optional[HistoryLog] = None) -> None:
        super().__init__()
        self._cfg = cfg
        self._log = log if log is not None else HistoryLog()
        self._alerts = AlertEngine(
            low_soc_pct=cfg.low_soc_warn_pct, recover_soc_pct=cfg.recover_soc_pct,
            imbalance_mv=cfg.imbalance_warn_mv,
        )
        self._failsafe = FailsafeMonitor(
            critical_soc_pct=cfg.critical_soc_pct, recover_soc_pct=cfg.recover_soc_pct,
            failsafe_timeout_sec=cfg.failsafe_timeout_sec, start_now=time.time(),
        )
        self._safety_actions = SafetyActions.from_config(cfg)
        self._prev_safe = True
        self._last: Optional[Reading] = None
        self._bank_readings: dict = {}        # mac -> last Reading (active pack for now)
        self._tray = None
        self.setWindowTitle(self.tr("ECO-WORTHY BMS Monitor") + f"  v{__version__}")
        self.setMinimumSize(720, 520)

        # pages
        self.monitor = MonitorPage(cfg.mac)
        self.bank = BankPage()
        self.cells = CellsPage()
        self.history = HistoryPage()
        self.messages = MessagesPage()
        self.settings = SettingsPage(cfg)
        self._pages = [self.monitor, self.bank, self.cells, self.history,
                       self.messages, self.settings]

        self._stack = QStackedWidget()
        for pg in self._pages:
            self._stack.addWidget(pg)

        # sidebar nav
        nav = QFrame(); nav.setObjectName("nav")
        nav.setFixedWidth(150)
        nv = QVBoxLayout(nav); nv.setContentsMargins(8, 14, 8, 14); nv.setSpacing(4)
        brand = QLabel("ECO-WORTHY"); brand.setObjectName("brand")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nv.addWidget(brand)
        ver = QLabel(f"v{__version__}"); ver.setObjectName("status")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nv.addWidget(ver)
        self._statusDot = QLabel("● disconnected"); self._statusDot.setObjectName("status")
        self._statusDot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nv.addWidget(self._statusDot)
        self._battery_combo = QComboBox()
        self._battery_combo.activated.connect(self._on_battery_selected)
        nv.addWidget(self._battery_combo)
        self._populate_battery_combo()
        nv.addSpacing(8)
        self._grp = QButtonGroup(self); self._grp.setExclusive(True)
        for i, name in enumerate(_NAV):
            b = QPushButton(self.tr(name)); b.setObjectName("navBtn"); b.setCheckable(True)
            b.clicked.connect(lambda _=False, idx=i: self._stack.setCurrentIndex(idx))
            self._grp.addButton(b, i)
            nv.addWidget(b)
        self._grp.button(0).setChecked(True)
        nv.addStretch(1)

        root = QHBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        root.addWidget(nav)
        root.addWidget(self._stack, 1)

        self.monitor.connectBtn.clicked.connect(self.connectToggled.emit)
        self.settings.connectRequested.connect(self.connectToggled.emit)
        self.settings.settingsApplied.connect(self._on_settings)

    # -- battery switcher ---------------------------------------------------
    def _populate_battery_combo(self) -> None:
        self._battery_combo.blockSignals(True)
        self._battery_combo.clear()
        profiles = profiles_from_config(self._cfg.batteries)
        for p in profiles:
            self._battery_combo.addItem(p.name, p.mac)
        # select the active pack
        idx = next((i for i, p in enumerate(profiles) if p.mac == self._cfg.mac), -1)
        if idx >= 0:
            self._battery_combo.setCurrentIndex(idx)
        self._battery_combo.setVisible(len(profiles) > 1)
        self._battery_combo.blockSignals(False)

    def _on_battery_selected(self, index: int) -> None:
        mac = self._battery_combo.itemData(index)
        if not mac or mac == self._cfg.mac:
            return
        self._cfg.mac = mac
        self.monitor.set_address(mac)
        self.readerReconfigured.emit(mac, self._cfg.poll_sec)

    def _refresh_bank(self) -> None:
        profiles = profiles_from_config(self._cfg.batteries)
        if profiles:
            rows = [(p.name, self._bank_readings.get(p.mac)) for p in profiles]
        else:
            rows = [("Battery", self._last)]
        self.bank.update_rows(rows)

    # -- tray ---------------------------------------------------------------
    def set_tray(self, tray) -> None:
        self._tray = tray
        if tray is not None:
            tray.notifications_enabled = self._cfg.notifications_enabled

    def closeEvent(self, event) -> None:
        if (self._cfg.minimize_to_tray and self._tray is not None
                and self._tray.is_available()):
            event.ignore()
            self.hide()
            self._tray.notify("ECO-WORTHY BMS", "Still running in the tray.")
        else:
            event.accept()

    # -- reader-facing slots ------------------------------------------------
    def on_status(self, s: str) -> None:
        self._statusDot.setText(f"● {s}")
        self.monitor.on_status(s)
        self.settings.set_connected(s in ("connected", "connecting"))
        self.messages.add_alerts(self._alerts.on_status(s))

    def on_reading(self, r: Reading) -> None:
        self._last = r
        f = self._cfg.fahrenheit
        self.monitor.on_reading(r, f)
        self.cells.on_reading(r, f)
        if self._log.append(r):
            self.history.refresh(self._log.recent())
        self.messages.add_alerts(self._alerts.on_reading(r))
        self._note_safety(self._failsafe.on_reading(r, time.time()))
        if self._tray is not None:
            self._tray.update_reading(r, r.state())
        self._bank_readings[self._cfg.mac] = r
        self._refresh_bank()

    # -- safety -------------------------------------------------------------
    def safety_is_safe(self) -> bool:
        s = self._failsafe.poll(time.time())
        self._note_safety(s)
        return s.is_safe

    def _note_safety(self, s: Safety) -> None:
        if s.is_safe == self._prev_safe:
            return
        self._prev_safe = s.is_safe
        if s.is_safe:
            self.messages.add_alerts([Alert(time.time(), Severity.INFO,
                                            Category.CRITICAL_RESERVE,
                                            f"Safety RE-ARMED — {s.reason}")])
            if self._tray is not None:
                self._tray.notify("BMS safety re-armed", s.reason)
        else:
            self.messages.add_alerts([Alert(time.time(), Severity.CRITICAL,
                                            Category.CRITICAL_RESERVE,
                                            f"UNSAFE — {s.reason}")])
            if self._tray is not None:
                self._tray.notify("BMS UNSAFE", s.reason, critical=True)
        self._dispatch_actions(s)

    def _dispatch_actions(self, s: Safety) -> None:
        if not self._safety_actions.any_enabled():
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self._safety_actions.fire(s, self._last))

    # -- settings -----------------------------------------------------------
    def _on_settings(self, cfg: AppConfig) -> None:
        mac_changed = cfg.mac != self._cfg.mac
        poll_changed = cfg.poll_sec != self._cfg.poll_sec
        alpaca_changed = (cfg.alpaca_enabled != self._cfg.alpaca_enabled
                          or cfg.alpaca_port != self._cfg.alpaca_port)
        autostart_changed = cfg.start_with_os != self._cfg.start_with_os
        self._cfg = cfg
        self._alerts.low_soc_pct = cfg.low_soc_warn_pct
        self._alerts.recover_soc_pct = cfg.recover_soc_pct
        self._alerts.imbalance_mv = cfg.imbalance_warn_mv
        self._failsafe.update_config(cfg.critical_soc_pct, cfg.recover_soc_pct,
                                     cfg.failsafe_timeout_sec)
        self._safety_actions = SafetyActions.from_config(cfg)
        self.monitor.set_address(cfg.mac)
        self._populate_battery_combo()
        self._refresh_bank()
        if self._tray is not None:
            self._tray.notifications_enabled = cfg.notifications_enabled
        if self._last is not None:
            self.cells.on_reading(self._last, cfg.fahrenheit)
        if autostart_changed:
            apply_autostart(cfg.start_with_os)
        if mac_changed or poll_changed:
            self.readerReconfigured.emit(cfg.mac, cfg.poll_sec)
        if alpaca_changed:
            self.alpacaReconfigured.emit(cfg.alpaca_enabled, cfg.alpaca_port)
