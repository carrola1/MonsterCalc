# -*- mode: python ; coding: utf-8 -*-

import sys


datas = [
    ("Monster.png", "."),
    ("MonsterHeader.png", "."),
    ("demo.txt", "."),
    ("release_notes.txt", "."),
    ("UserGuide.html", "."),
]

hiddenimports = []
if sys.platform == "win32":
    hiddenimports = [
        "PySide6",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "shiboken6",
    ]
icon_file = "Monster.icns" if sys.platform == "darwin" else "Monster.ico"

a = Analysis(
    ["MonsterCalc.py"],
    pathex=[],
    binaries=[],
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
    a.binaries,
    a.datas,
    [],
    name="MonsterCalc",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=icon_file,
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="MonsterCalc.app",
        icon=icon_file,
        bundle_identifier="com.andrewcarroll.monstercalc",
        info_plist={"NSHighResolutionCapable": "True"},
    )
