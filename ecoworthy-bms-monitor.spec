# -*- mode: python ; coding: utf-8 -*-
# Build (run on the target OS): pyinstaller --clean -y ecoworthy-bms-monitor.spec
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

hidden = (["ecoworthy_bmc1", "qasync"]
          + collect_submodules("aiohttp")
          + collect_submodules("bleak"))

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("ecoworthy_bms/theme.qss", "ecoworthy_bms"),
        ("resources/icon.png", "resources"),
    ],
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ECO-WORTHY-BMS-Monitor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,                 # windowed app, no console
    icon="resources/icon.ico",
)
