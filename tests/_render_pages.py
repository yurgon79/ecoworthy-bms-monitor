"""Render every page of the milestone-4 shell to PNGs (offscreen) so the full
app can be eyeballed without a live BLE link. Run from the project root:

    QT_QPA_PLATFORM=offscreen python tests/_render_pages.py
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ecoworthy_bms.config import AppConfig
from ecoworthy_bms.history import HistoryLog
from ecoworthy_bms.model import Reading
from ecoworthy_bms.ui.main_window import MainWindow, _NAV

app = QApplication([])
qss = Path("ecoworthy_bms/theme.qss")
if qss.exists():
    app.setStyleSheet(qss.read_text(encoding="utf-8"))
outdir = Path("preview"); outdir.mkdir(exist_ok=True)


def reading(soc, v, i, cells=(3.34, 3.35, 3.33, 3.34), temps=(23, 25, 25, 26)):
    return Reading(voltage_v=v, current_a=i, soc_pct=soc, soh_pct=100,
                   remaining_ah=1.5 * soc, full_ah=150.0, cycles=9,
                   cell_temps_c=temps, ambient_c=24, mosfet_c=28, cells_v=cells)


cfg = AppConfig()
log = HistoryLog(path=":memory:", min_interval_sec=0)
win = MainWindow(cfg, log=log)
win.resize(760, 560)

# seed a discharge curve for the history chart
win.on_status("connected")
for k in range(40):
    soc = 100 - k                       # 100 -> 61
    v = 14.4 - (k * 0.04)               # 14.4 -> 12.8
    win.on_reading(reading(soc, v, -8.0))

# trigger a few messages: imbalance, low-soc, BLE blip
win.on_reading(reading(58, 12.9, -8.0, cells=(3.18, 3.35, 3.18, 3.19)))  # imbalance
win.on_reading(reading(24, 12.6, -6.0))                                   # low soc
win.on_status("disconnected")
win.on_status("connected")
win.on_reading(reading(62, 13.4, 2.0))                                    # recover + charging

win.show(); app.processEvents()

for i, name in enumerate(_NAV):
    win._grp.button(i).setChecked(True)
    win._stack.setCurrentIndex(i)
    app.processEvents()
    f = outdir / f"m4_{i}_{name.lower()}.png"
    ok = win.grab().save(str(f))
    print(f"{'saved' if ok else 'FAILED'} {f}")
