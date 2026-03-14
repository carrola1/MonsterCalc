from __future__ import annotations

from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
ASSETS = {
    "app_icon": APP_DIR / "MonsterApp.png",
    "demo": APP_DIR / "demo.txt",
    "release_notes": APP_DIR / "release_notes.txt",
    "user_guide": APP_DIR / "UserGuide.html",
}


def resource_path(name: str) -> Path:
    return ASSETS[name]
