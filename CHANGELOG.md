# Changelog

Format based on [Keep a Changelog](https://keepachangelog.com/);
this project follows [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-06-18

First public release — a cross-platform desktop monitor built on the
`ecoworthy-bmc1-protocol` library.

### Added
- **Live monitor**: painted N-cell battery (fill = SOC, flow wire = current
  direction), SOC/voltage/current/power/runtime, charge/discharge/float/idle state.
- **Cells** page: per-cell balance bars + temperatures (°C/°F).
- **History** page: local SOC + voltage trend (SQLite, no cloud).
- **Messages**: edge-triggered alert log (low SOC, cell imbalance, BLE lost/restored).
- **Bank** page + battery **profiles/switcher**: manage multiple packs, switch the
  active one, see a whole-bank summary. (Concurrent multi-pack polling lands later.)
- **Critical-reserve safety** with pluggable actions: desktop notification, a shell
  command, a webhook POST, MQTT publish, and an embedded ASCOM **Alpaca SafetyMonitor**
  (for NINA astro automation).
- **System tray** (live SOC badge, minimize/close to tray, native notifications),
  **start at login**, cross-platform config/data dir.
- **i18n** scaffolding (English source; community translations via Qt Linguist).

### Notes
- Read-only: the app never writes to the BMS.
- Desktop only (Windows/macOS/Linux). Android is not supported (the BLE backend,
  `bleak`, has no Android support).
