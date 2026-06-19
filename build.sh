#!/usr/bin/env bash
# Build a standalone binary on macOS or Linux. Output: dist/ECO-WORTHY-BMS-Monitor
set -euo pipefail
cd "$(dirname "$0")"
python3 -m pip install --upgrade pyinstaller pyside6 qasync aiohttp bleak platformdirs ecoworthy-bmc1-protocol
python3 -m PyInstaller --clean -y ecoworthy-bms-monitor.spec
echo "Built: $(pwd)/dist/ECO-WORTHY-BMS-Monitor"
