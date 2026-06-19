"""Fail-safe state machine (milestone 5) — pure, no Qt/HTTP, unit-testable.

Drives the NINA SafetyMonitor. Direction is the opposite of a typical server watchdog:
the GEAR is the priority, so uncertainty fails to UNSAFE (park) rather than
riding it out. (SPEC §6.)

Rules:
  * SOC >= critical            -> SAFE  (plenty of reserve, regardless of flow)
  * SOC <  critical & charging -> SAFE  (external power present, being replenished)
  * SOC <  critical & on batt  -> UNSAFE (low reserve, draining/stalled) [latched]
  * recovery from a low-SOC trip needs SOC >= recover AND charging (hysteresis,
    so a value hovering at the threshold cannot flap the mount)
  * a brief BLE gap rides on last-known state; data older than `timeout`
    (incl. never receiving a first reading) -> UNSAFE (stale = unsafe)
  * startup grace == one `timeout` window before stale-unsafe can trip
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..model import Reading

_CHARGE_A = 0.3   # current above this => external power present (charging)


@dataclass(frozen=True)
class Safety:
    is_safe: bool
    reason: str


class FailsafeMonitor:
    def __init__(self, critical_soc_pct: int = 25, recover_soc_pct: int = 35,
                 failsafe_timeout_sec: float = 180.0, start_now: Optional[float] = None):
        self.critical = int(critical_soc_pct)
        self.recover = int(recover_soc_pct)
        self.timeout = float(failsafe_timeout_sec)
        self._latched_low = False
        self._last_reading_ts: Optional[float] = None
        self._started_ts = start_now
        self._safe = True
        self._reason = "starting up (grace window)"

    def update_config(self, critical_soc_pct: int, recover_soc_pct: int,
                      failsafe_timeout_sec: float) -> None:
        self.critical = int(critical_soc_pct)
        self.recover = int(recover_soc_pct)
        self.timeout = float(failsafe_timeout_sec)

    def on_reading(self, r: Reading, now: float) -> Safety:
        self._last_reading_ts = now
        charging = r.current_a > _CHARGE_A
        if self._latched_low:
            if r.soc_pct >= self.recover and charging:
                self._latched_low = False
        elif r.soc_pct < self.critical and not charging:
            self._latched_low = True

        if self._latched_low:
            return self._set(False,
                             f"SOC {r.soc_pct}% below critical {self.critical}% on battery")
        return self._set(True, f"SOC {r.soc_pct}% (reserve OK)")

    def poll(self, now: float) -> Safety:
        """Enforce staleness; call at every issafe query. Never flips stale->safe."""
        base = self._last_reading_ts
        if base is None:
            if self._started_ts is None:
                self._started_ts = now
            base = self._started_ts
        if (now - base) >= self.timeout:
            if self._last_reading_ts is None:
                return self._set(False, "no BMS data within fail-safe window")
            return self._set(False, f"BMS data stale > {int(self.timeout)}s (fail-safe)")
        return Safety(self._safe, self._reason)

    def current(self) -> Safety:
        return Safety(self._safe, self._reason)

    def _set(self, safe: bool, reason: str) -> Safety:
        self._safe = safe
        self._reason = reason
        return Safety(safe, reason)
