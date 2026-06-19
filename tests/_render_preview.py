"""Render the Monitor window to PNGs (offscreen) so the dashboard can be eyeballed
without a live BLE connection. Run from the project root."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
from PySide6.QtWidgets import QApplication
from ecoworthy_bms.ui.monitor import MonitorWindow
from ecoworthy_bms.model import Reading

app = QApplication([])
qss = Path("ecoworthy_bms/theme.qss")
if qss.exists():
    app.setStyleSheet(qss.read_text(encoding="utf-8"))
outdir = Path("preview"); outdir.mkdir(exist_ok=True)

def shot(name, r):
    w = MonitorWindow("52:EB:8C:7B:3A:FF")
    w.resize(560, 520)
    w.on_status("connected")
    w.on_reading(r)
    w.show(); app.processEvents()
    f = outdir / name
    ok = w.grab().save(str(f))
    print(f"{'saved' if ok else 'FAILED'} {f}")

shot("monitor_float_100.png", Reading(
    voltage_v=14.44, current_a=1.04, soc_pct=100, soh_pct=100,
    remaining_ah=149.26, full_ah=150.0, cycles=9, cell_temps_c=(23,26,26,26),
    ambient_c=24, mosfet_c=26, cells_v=(3.622,3.614,3.600,3.609)))
shot("monitor_discharge_62.png", Reading(
    voltage_v=12.9, current_a=-8.0, soc_pct=62, soh_pct=100,
    remaining_ah=92.0, full_ah=150.0, cycles=9, cell_temps_c=(24,25,25,26),
    ambient_c=24, mosfet_c=28, cells_v=(3.21,3.22,3.20,3.21)))
