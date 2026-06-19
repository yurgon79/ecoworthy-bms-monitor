"""Cells page: per-cell voltages with a balance bar (imbalance mV), plus the
four cell temperatures, ambient and MOSFET temps. SPEC §5 (Cells)."""
from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget,
)

from ..config import BRAND_BLUE, CRIT_RED, IDLE_GREY
from ..model import Reading, temp_str

# LiFePO4 per-cell display window (V) for the balance bars.
_V_LO, _V_HI = 2.80, 3.65


class _MetricTile(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("tile")
        lay = QVBoxLayout(self)
        t = QLabel(self.tr(title))
        t.setObjectName("tileTitle")
        self._v = QLabel("—")
        self._v.setObjectName("tileValue")
        lay.addWidget(t)
        lay.addWidget(self._v)

    def set(self, text: str) -> None:
        self._v.setText(text)

    def text(self) -> str:
        return self._v.text()


class _BalanceBars(QWidget):
    """Horizontal bar per cell within [_V_LO, _V_HI]; min cell blue, max red."""

    def __init__(self) -> None:
        super().__init__()
        self._cells: Sequence[float] = ()
        self.setMinimumHeight(150)

    def set_cells(self, cells_v: Sequence[float]) -> None:
        self._cells = tuple(cells_v)
        self.update()

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        if not self._cells:
            p.setPen(QColor(IDLE_GREY))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "no cell data")
            return
        vmin, vmax = min(self._cells), max(self._cells)
        n = len(self._cells)
        row_h = H / n
        label_w = 64.0
        val_w = 70.0
        track_x = label_w
        track_w = max(10.0, W - label_w - val_w)
        f = QFont(); f.setPointSize(10)
        p.setFont(f)
        for i, v in enumerate(self._cells):
            cy = i * row_h
            mid = cy + row_h / 2
            # label
            p.setPen(QColor("#14213d"))
            p.drawText(QRectF(0, cy, label_w - 6, row_h),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       f"Cell {i + 1}")
            # track
            bar_h = min(18.0, row_h * 0.5)
            track = QRectF(track_x, mid - bar_h / 2, track_w, bar_h)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#eef2f7"))
            p.drawRoundedRect(track, 4, 4)
            # fill
            frac = (v - _V_LO) / (_V_HI - _V_LO)
            frac = max(0.0, min(1.0, frac))
            color = QColor(BRAND_BLUE)
            if v == vmax and vmax != vmin:
                color = QColor(CRIT_RED)
            elif v == vmin and vmax != vmin:
                color = QColor("#2b6cb0")
            p.setBrush(color)
            p.drawRoundedRect(QRectF(track_x, mid - bar_h / 2,
                                     track_w * frac, bar_h), 4, 4)
            # value
            p.setPen(QColor("#14213d"))
            p.drawText(QRectF(track_x + track_w + 6, cy, val_w - 6, row_h),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                       f"{v:.3f} V")


class CellsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)

        cap = QLabel(self.tr("Cell voltages"))
        cap.setObjectName("section")
        root.addWidget(cap)
        self._bars = _BalanceBars()
        root.addWidget(self._bars)

        self._imbalance = QLabel(self.tr("Imbalance: —"))
        self._imbalance.setObjectName("imbalance")
        root.addWidget(self._imbalance)

        cap2 = QLabel(self.tr("Temperatures"))
        cap2.setObjectName("section")
        root.addWidget(cap2)
        self._grid = QGridLayout()
        root.addLayout(self._grid)
        root.addStretch(1)

        self._t_amb = _MetricTile("Ambient")
        self._t_mos = _MetricTile("MOSFET")
        self._t_cells: list = []
        self._n_cells = -1
        self._rebuild_temp_tiles(4)

    def _rebuild_temp_tiles(self, n: int) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
        self._t_cells = [_MetricTile(f"Cell {i + 1}") for i in range(max(1, n))]
        tiles = [*self._t_cells, self._t_amb, self._t_mos]
        for i, t in enumerate(tiles):
            self._grid.addWidget(t, i // 3, i % 3)
        self._n_cells = n

    def on_reading(self, r: Reading, fahrenheit: bool = False) -> None:
        self._bars.set_cells(r.cells_v)
        self._imbalance.setText(self.tr("Imbalance: {0} mV").format(f"{r.imbalance_mv:.0f}"))
        n = len(r.cell_temps_c)
        if n != self._n_cells:
            self._rebuild_temp_tiles(n)
        for i, t in enumerate(self._t_cells):
            if i < len(r.cell_temps_c):
                t.set(temp_str(r.cell_temps_c[i], fahrenheit))
        self._t_amb.set(temp_str(r.ambient_c, fahrenheit))
        self._t_mos.set(temp_str(r.mosfet_c, fahrenheit))
