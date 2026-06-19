"""History page: local SOC + voltage trend, painted from the SQLite log.
SPEC §5 (History). The app keeps its own history (no cloud)."""
from __future__ import annotations

import time
from typing import List, Sequence

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..config import BRAND_BLUE, DISCHARGE_ORANGE, IDLE_GREY
from ..history import Sample

_SOC_COLOR = QColor(BRAND_BLUE)
_V_COLOR = QColor(DISCHARGE_ORANGE)


class _TrendChart(QWidget):
    """SOC (filled area, 0–100% left axis) + voltage (line, auto-scaled right)."""

    def __init__(self) -> None:
        super().__init__()
        self._samples: List[Sample] = []
        self.setMinimumHeight(240)

    def set_samples(self, samples: Sequence[Sample]) -> None:
        self._samples = list(samples)
        self.update()

    def paintEvent(self, _ev) -> None:
        from PySide6.QtGui import QPainter
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        ml, mr, mt, mb = 38.0, 46.0, 14.0, 26.0
        plot = QRectF(ml, mt, W - ml - mr, H - mt - mb)

        # frame + horizontal gridlines (0/25/50/75/100% SOC)
        p.setPen(QPen(QColor("#e5e7eb"), 1))
        p.drawRect(plot)
        f = QFont(); f.setPointSize(8); p.setFont(f)
        for pct in (0, 25, 50, 75, 100):
            y = plot.bottom() - plot.height() * (pct / 100.0)
            p.setPen(QPen(QColor("#eef2f7"), 1))
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            p.setPen(QColor(IDLE_GREY))
            p.drawText(QRectF(0, y - 8, ml - 4, 16),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                       f"{pct}")

        n = len(self._samples)
        if n == 0:
            p.setPen(QColor(IDLE_GREY))
            p.drawText(plot, Qt.AlignmentFlag.AlignCenter, "no history yet")
            return

        def x_at(i: int) -> float:
            if n == 1:
                return plot.center().x()
            return plot.left() + plot.width() * (i / (n - 1))

        # SOC filled area
        soc_pts = [QPointF(x_at(i), plot.bottom() - plot.height() * (s.soc_pct / 100.0))
                   for i, s in enumerate(self._samples)]
        area = QPolygonF([QPointF(soc_pts[0].x(), plot.bottom()), *soc_pts,
                          QPointF(soc_pts[-1].x(), plot.bottom())])
        fill = QColor(_SOC_COLOR); fill.setAlpha(40)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(fill)
        p.drawPolygon(area)
        path = QPainterPath(soc_pts[0])
        for pt in soc_pts[1:]:
            path.lineTo(pt)
        p.setPen(QPen(_SOC_COLOR, 2)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

        # voltage line, auto-scaled
        vs = [s.voltage_v for s in self._samples]
        vlo, vhi = min(vs), max(vs)
        if vhi - vlo < 0.1:
            vlo, vhi = vlo - 0.05, vhi + 0.05
        vpath = QPainterPath()
        for i, s in enumerate(self._samples):
            y = plot.bottom() - plot.height() * ((s.voltage_v - vlo) / (vhi - vlo))
            pt = QPointF(x_at(i), y)
            vpath.moveTo(pt) if i == 0 else vpath.lineTo(pt)
        p.setPen(QPen(_V_COLOR, 2)); p.drawPath(vpath)
        # right-axis voltage range labels
        p.setPen(_V_COLOR)
        p.drawText(QRectF(plot.right() + 2, plot.top() - 4, mr - 2, 16),
                   Qt.AlignmentFlag.AlignLeft, f"{vhi:.2f}V")
        p.drawText(QRectF(plot.right() + 2, plot.bottom() - 12, mr - 2, 16),
                   Qt.AlignmentFlag.AlignLeft, f"{vlo:.2f}V")


class HistoryPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        cap = QLabel(self.tr("SOC & voltage trend"))
        cap.setObjectName("section")
        root.addWidget(cap)
        self._chart = _TrendChart()
        root.addWidget(self._chart, 1)

        legend = QHBoxLayout()
        soc_l = QLabel("■ SOC (%)"); soc_l.setStyleSheet(f"color:{BRAND_BLUE};")
        v_l = QLabel("■ Voltage (V)"); v_l.setStyleSheet(f"color:{DISCHARGE_ORANGE};")
        self._span = QLabel("—"); self._span.setObjectName("status")
        legend.addWidget(soc_l); legend.addWidget(v_l)
        legend.addStretch(1); legend.addWidget(self._span)
        root.addLayout(legend)

    def refresh(self, samples: Sequence[Sample]) -> None:
        self._chart.set_samples(samples)
        n = len(samples)
        if n >= 2:
            span_s = samples[-1].ts - samples[0].ts
            self._span.setText(f"{n} samples · {self._fmt_span(span_s)}")
        elif n == 1:
            self._span.setText("1 sample")
        else:
            self._span.setText("no history yet")

    @staticmethod
    def _fmt_span(seconds: float) -> str:
        m = int(seconds // 60)
        if m < 60:
            return f"{m} min"
        h, m = divmod(m, 60)
        if h < 24:
            return f"{h}h {m:02d}m"
        d, h = divmod(h, 24)
        return f"{d}d {h}h"
