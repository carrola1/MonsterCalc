# -*- mode: python ; coding: utf-8 -*-

import importlib.util
import sys
from PyInstaller.utils.hooks import collect_all


datas = [
    ("MonsterApp.png", "."),
    ("demo.txt", "."),
    ("release_notes.txt", "."),
    ("UserGuide.html", "."),
]


def require_build_dependency(module_name, install_hint):
    if importlib.util.find_spec(module_name) is None:
        raise SystemExit(
            f"Missing build dependency: {module_name}\n"
            f"Install it in the Python environment running PyInstaller.\n"
            f"Example:\n"
            f"  {install_hint}"
        )


require_build_dependency("PySide6", "python -m pip install PySide6")

qt_datas = []
qt_binaries = []
hiddenimports = []
if sys.platform == "win32":
    qt_datas, qt_binaries, hiddenimports = collect_all("PySide6")
    _, shiboken_binaries, shiboken_hiddenimports = collect_all("shiboken6")
    qt_binaries += shiboken_binaries
    hiddenimports += shiboken_hiddenimports
    hiddenimports = sorted(set(hiddenimports))

datas += qt_datas
icon_file = "Monster.icns" if sys.platform == "darwin" else "Monster.ico"

a = Analysis(
    ["MonsterCalc.py"],
    pathex=[],
    binaries=qt_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PyQt6", "PyQt6.QtCore", "PyQt6.QtGui", "PyQt6.QtWidgets"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MonsterCalc",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=icon_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MonsterCalc",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="MonsterCalc.app",
        icon=icon_file,
        bundle_identifier="com.andrewcarroll.monstercalc",
        info_plist={"NSHighResolutionCapable": "True"},
    )
