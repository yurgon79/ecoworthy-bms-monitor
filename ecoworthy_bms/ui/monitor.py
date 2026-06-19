"""Monitor (home) page: live SOC / V / I / power / runtime / state, with the
painted 4-cell battery hero (milestone 3) and connect controls.

Milestone 4: converted from a standalone window into a page hosted by
MainWindow. `MonitorWindow` kept as an alias for the render harness.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from ..widgets.battery_cells import BatteryCellsWidget
from ..model import PackState, Reading, runtime_str

_STATE_COLOR = {
    PackState.CHARGING: "#1fa14a",
    PackState.FLOAT: "#0a8ac0",
    PackState.DISCHARGING: "#c8761a",
    PackState.IDLE: "#6b7280",
    PackState.GRID_DOWN: "#c0392b",
    PackState.UNKNOWN: "#6b7280",
}


class _Tile(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("tile")
        lay = QVBoxLayout(self)
        self._title = QLabel(self.tr(title))
        self._title.setObjectName("tileTitle")
        self._value = QLabel("—")
        self._value.setObjectName("tileValue")
        lay.addWidget(self._title)
        lay.addWidget(self._value)

    def set(self, text: str) -> None:
        self._value.setText(text)

    def text(self) -> str:
        return self._value.text()


class MonitorPage(QWidget):
    def __init__(self, address: str) -> None:
        super().__init__()
        self.setWindowTitle(self.tr("ECO-WORTHY BMS — Monitor"))
        self.setMinimumSize(540, 460)
        root = QVBoxLayout(self)

        # header: address + connection status + connect/disconnect
        head = QHBoxLayout()
        self._addr = QLabel(address)
        self._addr.setObjectName("addr")
        self._statusDot = QLabel("● disconnected")
        self._statusDot.setObjectName("status")
        self.connectBtn = QPushButton("Connect")
        head.addWidget(self._addr)
        head.addStretch(1)
        head.addWidget(self._statusDot)
        head.addWidget(self.connectBtn)
        root.addLayout(head)

        # hero: painted 4-cell battery + state chip
        self._battery = BatteryCellsWidget()
        soc_row = QHBoxLayout()
        soc_row.addWidget(self._battery, 1)
        self._chip = QLabel("—")
        self._chip.setObjectName("chip")
        self._chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._chip.setFixedHeight(34)
        soc_row.addWidget(self._chip, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(soc_row)
        # hidden SOC label retained for programmatic/accessibility reads
        self._soc = QLabel("—%")
        self._soc.setObjectName("soc")
        self._soc.setVisible(False)

        # tiles
        grid = QGridLayout()
        self._t_v = _Tile("Voltage")
        self._t_i = _Tile("Current")
        self._t_p = _Tile("Power")
        self._t_rt = _Tile("Est. runtime")
        for i, t in enumerate((self._t_v, self._t_i, self._t_p, self._t_rt)):
            grid.addWidget(t, i // 2, i % 2)
        root.addLayout(grid)
        root.addStretch(1)

    def set_address(self, address: str) -> None:
        self._addr.setText(address)

    # -- slots --------------------------------------------------------------
    def on_status(self, s: str) -> None:
        self._statusDot.setText(f"● {s}")
        self.connectBtn.setText("Disconnect" if s in ("connected", "connecting") else "Connect")

    def on_reading(self, r: Reading, fahrenheit: bool = False) -> None:
        self._soc.setText(f"{r.soc_pct}%")
        self._battery.set_state(r.soc_pct, r.current_a, n_cells=len(r.cells_v))
        st = r.state()
        self._chip.setText(st.value)
        self._chip.setStyleSheet(
            f"#chip{{background:{_STATE_COLOR[st]};color:white;border-radius:8px;padding:4px 12px;}}"
        )
        self._t_v.set(f"{r.voltage_v:.2f} V")
        self._t_i.set(f"{r.current_a:+.2f} A")
        self._t_p.set(f"{r.power_w:+.1f} W")
        self._t_rt.set(runtime_str(r.runtime_h))


# Back-compat alias (render harness / earlier milestones referenced this name).
MonitorWindow = MonitorPage
