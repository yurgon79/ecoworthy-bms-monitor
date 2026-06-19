# Build the Windows .exe (run on Windows). Output: dist\ECO-WORTHY-BMS-Monitor.exe
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m pip install --upgrade pyinstaller pyside6 qasync aiohttp bleak platformdirs ecoworthy-bmc1-protocol
python -m PyInstaller --clean -y ecoworthy-bms-monitor.spec
Write-Host "`nBuilt: $(Resolve-Path .\dist\ECO-WORTHY-BMS-Monitor.exe)"
