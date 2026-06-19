"""Local history log (SQLite) — the app keeps its own SOC/voltage trend since
the BMS has no cloud. Pure logic, no Qt; unit-testable with an in-memory DB.

SPEC §5 (History) / §7 (history.py).
"""
from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .model import Reading

log = logging.getLogger("ecoworthy_bms.history")


@dataclass(frozen=True)
class Sample:
    ts: float          # unix seconds
    soc_pct: int
    voltage_v: float
    current_a: float


def default_db_path() -> Path:
    from .config import data_dir
    return data_dir() / "history.db"


class HistoryLog:
    """Append-only SOC/voltage trend. Coalesces samples to >= min_interval_sec
    so a fast poll cadence doesn't bloat the DB."""

    def __init__(self, path: Optional[Path] = None, min_interval_sec: float = 30.0):
        self._min_interval = float(min_interval_sec)
        self._last_ts: Optional[float] = None
        if path is None:
            path = default_db_path()
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path))
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS samples ("
            " ts REAL PRIMARY KEY, soc INTEGER, voltage REAL, current REAL)"
        )
        self._db.commit()

    def append(self, r: Reading, now: Optional[float] = None) -> bool:
        """Record a sample. Returns True if written, False if coalesced away."""
        t = time.time() if now is None else now
        if self._last_ts is not None and (t - self._last_ts) < self._min_interval:
            return False
        self._db.execute(
            "INSERT OR REPLACE INTO samples (ts, soc, voltage, current) VALUES (?,?,?,?)",
            (t, int(r.soc_pct), float(r.voltage_v), float(r.current_a)),
        )
        self._db.commit()
        self._last_ts = t
        return True

    def recent(self, limit: int = 500) -> List[Sample]:
        """Most-recent samples, returned oldest-first for plotting."""
        rows = self._db.execute(
            "SELECT ts, soc, voltage, current FROM samples ORDER BY ts DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
        return [Sample(ts, soc, v, c) for (ts, soc, v, c) in reversed(rows)]

    def count(self) -> int:
        return self._db.execute("SELECT COUNT(*) FROM samples").fetchone()[0]

    def close(self) -> None:
        try:
            self._db.close()
        except Exception:  # noqa: BLE001
            pass
