"""Entry point: Qt app on a qasync event loop so bleak's asyncio runs inside Qt.

Run:  python -m ecoworthy_bms [MAC]
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
import qasync

from .config import AppConfig
from .i18n import install_translator
from .reader_service import ReaderService
from .safety.alpaca import AlpacaSafetyServer
from .tray import SystemTray, render_soc_icon
from .ui.main_window import MainWindow


def _load_theme(app: QApplication) -> None:
    qss = Path(__file__).resolve().parent / "theme.qss"
    if qss.exists():
        app.setStyleSheet(qss.read_text(encoding="utf-8"))


def _app_icon() -> QIcon:
    png = Path(__file__).resolve().parent.parent / "resources" / "icon.png"
    return QIcon(str(png)) if png.exists() else render_soc_icon(None)


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    cfg = AppConfig.load()
    if len(sys.argv) > 1:
        cfg.mac = sys.argv[1]

    app = QApplication(sys.argv)
    install_translator(app)
    app.setQuitOnLastWindowClosed(False)   # tray keeps the app alive when hidden
    _load_theme(app)
    icon = _app_icon()
    app.setWindowIcon(icon)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    win = MainWindow(cfg)

    # system tray (M7) — only if the desktop offers one
    tray = None
    if SystemTray.is_available():
        tray = SystemTray(app, win, icon)
        tray.notifications_enabled = cfg.notifications_enabled
        win.set_tray(tray)
        tray.start()

    # mutable handles so reconfigure can swap the services
    state = {"svc": ReaderService(cfg.mac, poll_sec=cfg.poll_sec),
             "connected": False, "alpaca": None}

    def _bind(svc: ReaderService) -> None:
        svc.status.connect(win.on_status)
        svc.reading.connect(win.on_reading)
        svc.error.connect(lambda m: logging.getLogger("ui").warning("reader: %s", m))

    _bind(state["svc"])

    def _toggle() -> None:
        svc = state["svc"]
        if state["connected"]:
            asyncio.ensure_future(svc.stop())
            state["connected"] = False
        else:
            svc.start()
            state["connected"] = True
    win.connectToggled.connect(_toggle)

    def _reconfigure(mac: str, poll: float) -> None:
        async def _swap() -> None:
            await state["svc"].stop()
            svc = ReaderService(mac, poll_sec=poll)
            _bind(svc)
            state["svc"] = svc
            svc.start()
            state["connected"] = True
        asyncio.ensure_future(_swap())
    win.readerReconfigured.connect(_reconfigure)

    async def _start_alpaca(port: int) -> None:
        srv = AlpacaSafetyServer(win.safety_is_safe, port=port)
        await srv.start()
        state["alpaca"] = srv

    def _alpaca_reconfigure(enabled: bool, port: int) -> None:
        async def _swap() -> None:
            if state["alpaca"] is not None:
                await state["alpaca"].stop()
                state["alpaca"] = None
            if enabled:
                await _start_alpaca(port)
        asyncio.ensure_future(_swap())
    win.alpacaReconfigured.connect(_alpaca_reconfigure)

    if cfg.start_minimized and tray is not None:
        pass                       # boot straight to the tray
    else:
        win.show()
    if cfg.mac:                    # auto-connect on launch only if a MAC is set
        state["svc"].start()
        state["connected"] = True
    if cfg.alpaca_enabled:
        asyncio.ensure_future(_start_alpaca(cfg.alpaca_port))

    with loop:
        loop.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
