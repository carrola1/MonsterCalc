from __future__ import annotations

import sys
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent


def _window_icon_path() -> Path:
    if sys.platform.startswith("win"):
        icon_path = APP_DIR / "Monster.ico"
        if icon_path.exists():
            return icon_path
    return APP_DIR / "MonsterApp.png"


ASSETS = {
    "app_icon": APP_DIR / "MonsterApp.png",
    "window_icon": _window_icon_path(),
    "demo": APP_DIR / "demo.txt",
    "release_notes": APP_DIR / "release_notes.txt",
    "user_guide": APP_DIR / "UserGuide.html",
}


def resource_path(name: str) -> Path:
    return ASSETS[name]
