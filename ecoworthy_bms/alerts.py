"""Alert derivation — pure, edge-triggered, no Qt. Feeds the Messages page.

M4 categories: LOW_SOC, IMBALANCE, BLE. The GRID and CRITICAL_RESERVE
categories are defined now but only fire once the M5 safety layer supplies a
grid signal / trip — kept here so the Messages UI and log schema are stable.

Edge-triggered: an alert fires on ENTERING a condition and a paired INFO fires
on RECOVERY, with hysteresis so a value hovering at the threshold can't spam.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from .model import Reading


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Category(str, Enum):
    LOW_SOC = "low-soc"
    IMBALANCE = "imbalance"
    BLE = "ble"
    GRID = "grid"                      # M5
    CRITICAL_RESERVE = "critical-reserve"  # M5


@dataclass(frozen=True)
class Alert:
    ts: float
    severity: Severity
    category: Category
    text: str


class AlertEngine:
    """Stateful edge detector. `on_reading` / `on_status` return any NEW alerts."""

    def __init__(self, low_soc_pct: int = 30, recover_soc_pct: int = 35,
                 imbalance_mv: int = 120, imbalance_clear_mv: int = 90):
        self.low_soc_pct = low_soc_pct
        self.recover_soc_pct = recover_soc_pct
        self.imbalance_mv = imbalance_mv
        self.imbalance_clear_mv = imbalance_clear_mv
        self._soc_low = False
        self._imbalanced = False
        self._ble_connected: Optional[bool] = None

    @staticmethod
    def _now(now: Optional[float]) -> float:
        return time.time() if now is None else now

    def on_reading(self, r: Reading, now: Optional[float] = None) -> List[Alert]:
        t = self._now(now)
        out: List[Alert] = []

        # --- low SOC (enter <= low; clear only above recover, hysteresis) ---
        if not self._soc_low and r.soc_pct <= self.low_soc_pct:
            self._soc_low = True
            out.append(Alert(t, Severity.WARNING, Category.LOW_SOC,
                             f"Low state of charge: {r.soc_pct}%"))
        elif self._soc_low and r.soc_pct >= self.recover_soc_pct:
            self._soc_low = False
            out.append(Alert(t, Severity.INFO, Category.LOW_SOC,
                             f"State of charge recovered: {r.soc_pct}%"))

        # --- cell imbalance ---
        imb = r.imbalance_mv
        if not self._imbalanced and imb >= self.imbalance_mv:
            self._imbalanced = True
            out.append(Alert(t, Severity.WARNING, Category.IMBALANCE,
                             f"Cell imbalance high: {imb:.0f} mV"))
        elif self._imbalanced and imb <= self.imbalance_clear_mv:
            self._imbalanced = False
            out.append(Alert(t, Severity.INFO, Category.IMBALANCE,
                             f"Cell imbalance cleared: {imb:.0f} mV"))

        return out

    def on_status(self, status: str, now: Optional[float] = None) -> List[Alert]:
        """BLE connectivity edges. `status` is the ReaderService string."""
        t = self._now(now)
        out: List[Alert] = []
        connected = status == "connected"
        if status in ("connected", "disconnected"):
            if self._ble_connected is None:
                self._ble_connected = connected
            elif connected != self._ble_connected:
                self._ble_connected = connected
                if connected:
                    out.append(Alert(t, Severity.INFO, Category.BLE,
                                     "BLE link restored"))
                else:
                    out.append(Alert(t, Severity.WARNING, Category.BLE,
                                     "BLE link lost"))
        return out
