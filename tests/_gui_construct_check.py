"""Headless construction smoke for the M2 shell (QT_QPA_PLATFORM=offscreen).
Verifies imports, signal/slot wiring, and that a real reading renders."""
import os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import qasync  # noqa: F401 — verify the asyncio<->Qt bridge imports
from PySide6.QtWidgets import QApplication
from ecoworthy_bms.ui.monitor import MonitorWindow
from ecoworthy_bms.reader_service import ReaderService
from ecoworthy_bms.model import Reading

app = QApplication([])
win = MonitorWindow("52:EB:8C:7B:3A:FF")
svc = ReaderService("52:EB:8C:7B:3A:FF")
svc.status.connect(win.on_status)
svc.reading.connect(win.on_reading)

win.on_status("connected")
win.on_reading(Reading(
    voltage_v=14.44, current_a=1.04, soc_pct=100, soh_pct=100,
    remaining_ah=149.26, full_ah=150.0, cycles=9,
    cell_temps_c=(23, 26, 26, 26), ambient_c=24, mosfet_c=26,
    cells_v=(3.622, 3.614, 3.600, 3.609),
))
assert "100%" in win._soc.text(), win._soc.text()
assert "14.44" in win._t_v.text(), win._t_v.text()
print(f"GUI_CONSTRUCT_OK soc={win._soc.text()} v={win._t_v.text()} "
      f"i={win._t_i.text()} p={win._t_p.text()} chip={win._chip.text()}")
