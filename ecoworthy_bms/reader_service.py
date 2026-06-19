"""Async BLE poller bridged to Qt via signals (runs on the qasync loop).

Wraps the published, read-only `ecoworthy_bmc1.BMC1Reader`. Emits a `Reading`
on every successful poll and a textual connection status. Auto-reconnects.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from PySide6.QtCore import QObject, Signal

from ecoworthy_bmc1 import BMC1Reader
from .model import Reading

log = logging.getLogger("ecoworthy_bms.reader")


class ReaderService(QObject):
    reading = Signal(object)   # Reading
    status = Signal(str)       # "connecting" | "connected" | "disconnected"
    error = Signal(str)

    def __init__(self, address: str, poll_sec: float = 5.0) -> None:
        super().__init__()
        self._address = address
        self._poll = poll_sec
        self._stop = asyncio.Event()
        self._task: Optional[asyncio.Future] = None

    def start(self) -> None:
        self._stop.clear()
        self._task = asyncio.ensure_future(self._run())

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            try:
                await self._task
            except Exception:
                pass

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.status.emit("connecting")
                async with BMC1Reader(self._address) as r:
                    self.status.emit("connected")
                    while not self._stop.is_set():
                        m = await r.read_main()
                        c = await r.read_cells()
                        self.reading.emit(Reading(
                            voltage_v=m.voltage_v, current_a=m.current_a,
                            soc_pct=m.soc_pct, soh_pct=m.soh_pct,
                            remaining_ah=m.remaining_ah, full_ah=m.full_ah,
                            cycles=m.cycles, cell_temps_c=tuple(m.cell_temps_c),
                            ambient_c=m.ambient_c, mosfet_c=m.mosfet_c,
                            cells_v=tuple(c.cells_v),
                        ))
                        await self._interruptible_sleep(self._poll)
            except Exception as e:  # noqa: BLE001 — surface, then retry
                if self._stop.is_set():
                    break
                self.status.emit("disconnected")
                self.error.emit(f"{type(e).__name__}: {e}")
                log.warning("reader loop error: %s", e)
                await self._interruptible_sleep(3.0)
        self.status.emit("disconnected")

    async def _interruptible_sleep(self, secs: float) -> None:
        try:
            await asyncio.wait_for(self._stop.wait(), timeout=secs)
        except asyncio.TimeoutError:
            pass
