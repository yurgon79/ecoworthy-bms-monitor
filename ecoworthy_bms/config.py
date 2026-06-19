"""App configuration: defaults, JSON persistence, brand palette, and the
cross-platform per-user data directory.

Pure (no Qt) so it stays unit-testable.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

log = logging.getLogger("ecoworthy_bms.config")

APP_DIRNAME = "ecoworthy-bms-monitor"
DEFAULT_MAC = ""   # set your battery's BLE MAC in Settings (or pass on the CLI)

# --- brand palette (mined from the ECO-WORTHY app) --------------------------
BRAND_BLUE = "#02339A"
FILL_TOP = "#4f86f7"
CHARGE_GREEN = "#1fa14a"
DISCHARGE_ORANGE = "#e07a1a"
IDLE_GREY = "#94a3b8"
WARN_AMBER = "#d98a0b"
CRIT_RED = "#c0392b"


def data_dir() -> Path:
    """Per-user data directory, cross-platform. Prefers `platformdirs`."""
    try:
        from platformdirs import user_data_dir
        return Path(user_data_dir(APP_DIRNAME, appauthor=False))
    except Exception:  # noqa: BLE001 — dependency optional; fall back per-OS
        if sys.platform == "win32":
            base = os.environ.get("APPDATA") or str(Path.home())
        elif sys.platform == "darwin":
            base = str(Path.home() / "Library" / "Application Support")
        else:
            base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        return Path(base) / APP_DIRNAME


def config_path() -> Path:
    return data_dir() / "config.json"


@dataclass
class AppConfig:
    mac: str = DEFAULT_MAC          # the ACTIVE battery's MAC
    batteries: list = field(default_factory=list)  # roster: [[name, mac], ...]
    poll_sec: float = 5.0
    fahrenheit: bool = False

    # --- safety gates (low-reserve protection; used by the optional safety layer) ---
    critical_soc_pct: int = 25
    failsafe_timeout_sec: int = 180
    recover_soc_pct: int = 35

    # --- message thresholds ---
    low_soc_warn_pct: int = 30
    imbalance_warn_mv: int = 120

    # --- safety / astro (ASCOM Alpaca SafetyMonitor; opt-in) ---
    alpaca_enabled: bool = False
    alpaca_port: int = 11111

    # --- window + tray QoL ---
    start_with_os: bool = False
    minimize_to_tray: bool = True
    start_minimized: bool = False
    notifications_enabled: bool = True

    # --- pluggable safety actions (fire on safety transitions; all opt-in) ---
    on_transition_command: str = ""   # shell command; tokens {state}{reason}{soc}{voltage}
    webhook_url: str = ""             # POST JSON payload on each transition
    mqtt_enabled: bool = False
    mqtt_host: str = ""
    mqtt_port: int = 1883
    mqtt_topic: str = "ecoworthy/bms/safety"

    # -- persistence --------------------------------------------------------
    def save(self, path: Path | None = None) -> None:
        p = path or config_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | None = None) -> "AppConfig":
        p = path or config_path()
        if not p.exists():
            return cls()
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001 — corrupt file -> defaults, don't crash
            log.warning("config load failed (%s); using defaults", e)
            return cls()
        known = {f.name for f in fields(cls)}
        cfg = cls(**{k: v for k, v in data.items() if k in known})
        if not cfg.batteries and cfg.mac:
            cfg.batteries = [["Battery", cfg.mac]]
        return cfg
