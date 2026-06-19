"""Battery profiles + bank aggregation (v0.2). Pure logic, no Qt/BLE.

A profile is just a friendly name + BLE MAC. The roster lets the user keep
several packs and switch the active one; the bank summary aggregates the
last-known reading of each pack for a whole-bank view.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from .model import Reading


@dataclass(frozen=True)
class Profile:
    name: str
    mac: str


def parse_profiles(text: str) -> List[Profile]:
    """One `Name = MAC` per line (or bare `MAC`); blank/`#` lines ignored."""
    out: List[Profile] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            name, mac = line.split("=", 1)
        else:
            name, mac = line, line
        name, mac = name.strip(), mac.strip()
        if mac:
            out.append(Profile(name or mac, mac))
    return out


def profiles_from_config(batteries: Sequence) -> List[Profile]:
    """`batteries` is a list of [name, mac] pairs (as persisted in JSON)."""
    out: List[Profile] = []
    for item in batteries or []:
        try:
            name, mac = item[0], item[1]
        except (TypeError, IndexError, KeyError):
            continue
        if mac:
            out.append(Profile(str(name) or str(mac), str(mac)))
    return out


def profiles_to_config(profiles: Sequence[Profile]) -> list:
    return [[p.name, p.mac] for p in profiles]


@dataclass(frozen=True)
class BankSummary:
    n: int
    soc_pct: int
    current_a: float
    power_w: float
    remaining_ah: float
    full_ah: float
    min_cell_v: float
    max_cell_v: float

    @property
    def imbalance_mv(self) -> float:
        return (self.max_cell_v - self.min_cell_v) * 1000.0 if self.max_cell_v else 0.0


def aggregate_bank(readings: Sequence[Optional[Reading]]) -> BankSummary:
    rs = [r for r in readings if r is not None]
    if not rs:
        return BankSummary(0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    full = sum(r.full_ah for r in rs)
    rem = sum(r.remaining_ah for r in rs)
    soc = round(100.0 * rem / full) if full > 0 else round(sum(r.soc_pct for r in rs) / len(rs))
    cur = sum(r.current_a for r in rs)
    pw = sum(r.power_w for r in rs)
    cells = [v for r in rs for v in r.cells_v]
    mn = min(cells) if cells else 0.0
    mx = max(cells) if cells else 0.0
    return BankSummary(len(rs), int(soc), round(cur, 2), round(pw, 1),
                       round(rem, 1), round(full, 1), mn, mx)
