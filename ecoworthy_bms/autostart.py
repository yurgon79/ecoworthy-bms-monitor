"""Start-with-OS, cross-platform.

Windows  -> HKCU\...\Run registry value
Linux    -> ~/.config/autostart/<app>.desktop (XDG autostart)
macOS    -> ~/Library/LaunchAgents/<id>.plist (launchd)

Each returns True on success, False if unsupported. Never raises.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

log = logging.getLogger("ecoworthy_bms.autostart")

_APP_ID = "ecoworthy-bms-monitor"
_APP_NAME = "ECO-WORTHY BMS Monitor"
_WIN_VALUE = "EcoworthyBmsMonitor"
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def launch_command() -> str:
    """Command the OS runs at login. Frozen build runs itself; dev runs the module."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    return f'"{sys.executable}" -m ecoworthy_bms'


def apply_autostart(enabled: bool) -> bool:
    if sys.platform == "win32":
        return _windows(enabled)
    if sys.platform == "darwin":
        return _macos(enabled)
    if sys.platform.startswith("linux"):
        return _linux(enabled)
    log.info("autostart unsupported on platform %s", sys.platform)
    return False


# -- Windows ---------------------------------------------------------------
def _windows(enabled: bool) -> bool:
    try:
        import winreg
    except ImportError:
        return False
    try:
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0,
                                 winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE)
        except OSError:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, _RUN_KEY)
        try:
            if enabled:
                winreg.SetValueEx(key, _WIN_VALUE, 0, winreg.REG_SZ, launch_command())
            else:
                try:
                    winreg.DeleteValue(key, _WIN_VALUE)
                except FileNotFoundError:
                    pass
            return True
        finally:
            winreg.CloseKey(key)
    except OSError as e:
        log.warning("Windows autostart failed: %s", e)
        return False


# -- Linux (XDG autostart) -------------------------------------------------
def _linux(enabled: bool) -> bool:
    import os
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    path = Path(base) / "autostart" / f"{_APP_ID}.desktop"
    try:
        if enabled:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "[Desktop Entry]\nType=Application\n"
                f"Name={_APP_NAME}\nExec={launch_command()}\n"
                "X-GNOME-Autostart-enabled=true\nTerminal=false\n",
                encoding="utf-8")
        elif path.exists():
            path.unlink()
        return True
    except OSError as e:
        log.warning("Linux autostart failed: %s", e)
        return False


# -- macOS (launchd LaunchAgent) -------------------------------------------
def _macos(enabled: bool) -> bool:
    label = "com.ecoworthy.bmsmonitor"
    path = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
    try:
        if enabled:
            exe = sys.executable
            args = f"<string>{exe}</string>" if getattr(sys, "frozen", False) else (
                f"<string>{exe}</string><string>-m</string><string>ecoworthy_bms</string>")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                '<plist version="1.0"><dict>'
                f'<key>Label</key><string>{label}</string>'
                f'<key>ProgramArguments</key><array>{args}</array>'
                '<key>RunAtLoad</key><true/></dict></plist>\n',
                encoding="utf-8")
        elif path.exists():
            path.unlink()
        return True
    except OSError as e:
        log.warning("macOS autostart failed: %s", e)
        return False
