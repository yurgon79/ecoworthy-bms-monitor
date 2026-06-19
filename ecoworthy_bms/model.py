"""Data model + derived metrics for the ECO-WORTHY BMS Windows app.

Pure logic, no Qt or BLE imports — unit-testable offline.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class PackState(str, Enum):
    CHARGING = "charging"
    FLOAT = "float"
    DISCHARGING = "discharging"
    IDLE = "idle"
    GRID_DOWN = "grid-down"   # reserved for milestone 5 (needs a grid signal)
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Reading:
    """One unified snapshot, assembled from cmd 0x21 + 0x22."""
    voltage_v: float
    current_a: float                     # + charge / - discharge
    soc_pct: int
    soh_pct: int
    remaining_ah: float
    full_ah: float
    cycles: int
    cell_temps_c: Tuple[int, ...]
    ambient_c: int
    mosfet_c: int
    cells_v: Tuple[float, ...]

    @property
    def power_w(self) -> float:
        return self.voltage_v * self.current_a

    @property
    def imbalance_mv(self) -> float:
        return (max(self.cells_v) - min(self.cells_v)) * 1000.0 if self.cells_v else 0.0

    @property
    def runtime_h(self) -> Optional[float]:
        """Hours to empty at the present discharge rate; None unless discharging."""
        if self.current_a < -0.05:
            return self.remaining_ah / abs(self.current_a)
        return None

    def state(self, charge_a: float = 0.3, idle_a: float = 0.05,
              float_soc: int = 99, float_a: float = 2.0) -> PackState:
        i = self.current_a
        if i > charge_a:
            if self.soc_pct >= float_soc and i < float_a:
                return PackState.FLOAT
            return PackState.CHARGING
        if i < -idle_a:
            return PackState.DISCHARGING
        return PackState.IDLE


def runtime_str(hours: Optional[float]) -> str:
    if hours is None:
        return "—"
    h = int(hours)
    m = int(round((hours - h) * 60))
    if m == 60:
        h, m = h + 1, 0
    return f"{h}h {m:02d}m"


def temp_str(celsius: float, fahrenheit: bool = False) -> str:
    """Format a raw protocol temperature (°C) for display, honoring the toggle."""
    if fahrenheit:
        return f"{celsius * 9 / 5 + 32:.0f}°F"
    return f"{celsius:.0f}°C"
