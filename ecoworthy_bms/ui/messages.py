"""Messages page: chronological alert log (newest first). SPEC §5 (Messages).

Alerts are produced by the pure `AlertEngine`; this page only renders them.
"""
from __future__ import annotations

import time
from typing import Iterable, List

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget,
)

from ..alerts import Alert, Severity
from ..config import CRIT_RED, IDLE_GREY, WARN_AMBER

_SEV_COLOR = {
    Severity.INFO: IDLE_GREY,
    Severity.WARNING: WARN_AMBER,
    Severity.CRITICAL: CRIT_RED,
}


class MessagesPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._count = 0
        root = QVBoxLayout(self)
        cap = QLabel(self.tr("Messages"))
        cap.setObjectName("section")
        root.addWidget(cap)
        self._empty = QLabel(self.tr("No messages."))
        self._empty.setObjectName("status")
        root.addWidget(self._empty)
        self._list = QListWidget()
        self._list.setObjectName("msglist")
        root.addWidget(self._list, 1)

    def add_alerts(self, alerts: Iterable[Alert]) -> None:
        added = 0
        for a in alerts:
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(a.ts))
            item = QListWidgetItem(f"{ts}   {a.severity.value.upper():8s} {a.text}")
            item.setForeground(QColor(_SEV_COLOR.get(a.severity, IDLE_GREY)))
            self._list.insertItem(0, item)   # newest on top
            added += 1
        self._count += added
        if self._count:
            self._empty.setVisible(False)

    def clear(self) -> None:
        self._list.clear()
        self._count = 0
        self._empty.setVisible(True)
