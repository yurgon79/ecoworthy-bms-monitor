"""Bank page (v0.2): whole-bank totals across all battery profiles + a per-pack
list. Aggregation is the pure `profiles.aggregate_bank`; this only renders."""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget,
)

from ..config import BRAND_BLUE, CHARGE_GREEN, DISCHARGE_ORANGE, IDLE_GREY
from ..model import Reading
from ..profiles import aggregate_bank

Row = Tuple[str, Optional[Reading]]


class _Tile(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("tile")
        lay = QVBoxLayout(self)
        t = QLabel(self.tr(title)); t.setObjectName("tileTitle")
        self._v = QLabel("—"); self._v.setObjectName("tileValue")
        lay.addWidget(t); lay.addWidget(self._v)

    def set(self, text: str) -> None:
        self._v.setText(text)


class BankPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.addWidget(_section(self.tr("Battery bank")))

        self._soc = QLabel("—%"); self._soc.setObjectName("soc")
        self._soc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._soc)

        grid = QGridLayout()
        self._t_packs = _Tile("Packs")
        self._t_i = _Tile("Bank current")
        self._t_p = _Tile("Bank power")
        self._t_cap = _Tile("Remaining / full")
        self._t_imb = _Tile("Imbalance")
        for i, t in enumerate((self._t_packs, self._t_i, self._t_p, self._t_cap, self._t_imb)):
            grid.addWidget(t, i // 3, i % 3)
        root.addLayout(grid)

        root.addWidget(_section(self.tr("Packs")))
        self._list = QListWidget(); self._list.setObjectName("msglist")
        root.addWidget(self._list, 1)

    def update_rows(self, rows: Sequence[Row]) -> None:
        summary = aggregate_bank([r for _, r in rows])
        self._soc.setText(f"{summary.soc_pct}%")
        self._t_packs.set(f"{summary.n} / {len(rows)} online")
        self._t_i.set(f"{summary.current_a:+.2f} A")
        self._t_p.set(f"{summary.power_w:+.1f} W")
        self._t_cap.set(f"{summary.remaining_ah:.0f} / {summary.full_ah:.0f} Ah")
        self._t_imb.set(f"{summary.imbalance_mv:.0f} mV")
        self._list.clear()
        for name, r in rows:
            if r is None:
                item = QListWidgetItem(f"{name:18s}  —  offline")
                item.setForeground(QColor(IDLE_GREY))
            else:
                st = r.state()
                color = {"charging": CHARGE_GREEN, "discharging": DISCHARGE_ORANGE}.get(
                    st.value, BRAND_BLUE)
                item = QListWidgetItem(
                    f"{name:18s}  {r.soc_pct:3d}%   {r.voltage_v:6.2f} V   "
                    f"{r.current_a:+6.2f} A   {st.value}")
                item.setForeground(QColor(color))
            self._list.addItem(item)


def _section(text: str) -> QLabel:
    lbl = QLabel(text); lbl.setObjectName("section")
    return lbl
