"""Signature dashboard visual: a 4-cell battery painted live.

Liquid fill height = SOC; the top flow wire's color + arrow direction encodes
current sign (charge vs discharge). Custom-painted — the vendor's PNG frames
are NOT shipped (SPEC §3). Driven by `set_state(soc_pct, current_a)`.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF,
)
from PySide6.QtWidgets import QWidget

from ..config import BRAND_BLUE

_DEFAULT_CELLS = 4
_CHARGE_A = 0.3
_IDLE_A = 0.05


class BatteryCellsWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._soc = 0
        self._current = 0.0
        self._n = _DEFAULT_CELLS
        self.setMinimumSize(320, 220)

    def set_state(self, soc_pct: int, current_a: float, n_cells=None) -> None:
        self._soc = int(max(0, min(100, soc_pct)))
        self._current = float(current_a)
        if n_cells:
            self._n = max(1, min(16, int(n_cells)))
        self.update()

    # -- painting -----------------------------------------------------------
    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        pad = 16.0
        wire_zone = 34.0
        body = QRectF(pad, pad + wire_zone, W - 2 * pad, H - 2 * pad - wire_zone)

        soc = self._soc / 100.0
        charging = self._current > _CHARGE_A
        discharging = self._current < -_IDLE_A

        gap = 10.0
        cw = (body.width() - (self._n - 1) * gap) / self._n
        fill_top = QColor("#4f86f7")
        fill_bot = QColor(BRAND_BLUE)
        if discharging:
            fill_top, fill_bot = QColor("#e8973c"), QColor("#c8761a")

        cell_centers = []
        for i in range(self._n):
            x = body.left() + i * (cw + gap)
            cell = QRectF(x, body.top(), cw, body.height())
            cell_centers.append(cell.center().x())

            p.setPen(QPen(QColor("#cbd5e1"), 2))
            p.setBrush(QColor("#f1f5f9"))
            p.drawRoundedRect(cell, 6, 6)

            fh = cell.height() * soc
            if fh > 0:
                fr = QRectF(cell.left(), cell.bottom() - fh, cell.width(), fh)
                grad = QLinearGradient(fr.topLeft(), fr.bottomLeft())
                grad.setColorAt(0.0, fill_top)
                grad.setColorAt(1.0, fill_bot)
                clip = QPainterPath()
                clip.addRoundedRect(cell, 6, 6)
                p.save()
                p.setClipPath(clip)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(grad))
                p.drawRect(fr)
                p.setPen(QPen(QColor(255, 255, 255, 150), 2))
                p.drawLine(fr.topLeft(), fr.topRight())
                p.restore()

        # terminals: red (+) over first cell, blue (-) over last
        post_w, post_h = 14.0, 10.0
        lx = cell_centers[0] - post_w / 2
        rx = cell_centers[-1] - post_w / 2
        ty = body.top() - post_h
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#d23b3b"))
        p.drawRect(QRectF(lx, ty, post_w, post_h))
        p.setBrush(QColor("#2b6cb0"))
        p.drawRect(QRectF(rx, ty, post_w, post_h))

        # flow wire across the top + direction arrows
        wire_y = pad + wire_zone / 2
        flow = (QColor("#1fa14a") if charging
                else QColor("#e07a1a") if discharging
                else QColor("#94a3b8"))
        p.setPen(QPen(QColor("#94a3b8"), 3))
        p.drawLine(QPointF(lx + post_w / 2, ty), QPointF(lx + post_w / 2, wire_y))
        p.drawLine(QPointF(rx + post_w / 2, ty), QPointF(rx + post_w / 2, wire_y))
        p.drawLine(QPointF(lx + post_w / 2, wire_y), QPointF(rx + post_w / 2, wire_y))

        if charging or discharging:
            self._draw_arrows(p, lx + post_w / 2, rx + post_w / 2, wire_y, flow, charging)

        # SOC % centred on the pack
        p.setPen(QColor("white") if soc > 0.5 else QColor(BRAND_BLUE))
        f = QFont()
        f.setPointSize(30)
        f.setBold(True)
        p.setFont(f)
        p.drawText(body, Qt.AlignmentFlag.AlignCenter, f"{self._soc}%")

    def _draw_arrows(self, p, x0, x1, y, color, into_battery):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        span = x1 - x0
        for k in (0.3, 0.5, 0.7):
            cx = x0 + span * k
            # charge: point left->battery terminals (outward to posts); discharge: inward
            d = 7.0 if into_battery else -7.0
            tri = QPolygonF([
                QPointF(cx - d, y - 6),
                QPointF(cx + d, y),
                QPointF(cx - d, y + 6),
            ])
            p.drawPolygon(tri)
