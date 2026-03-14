#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_PATH="${1:-$SCRIPT_DIR/dist/MonsterCalc/MonsterCalc}"

if [[ ! -e "$APP_PATH" ]]; then
  echo "MonsterCalc executable not found: $APP_PATH" >&2
  echo "Pass the path to the built executable, for example:" >&2
  echo "  ./install_linux.sh ./dist/MonsterCalc/MonsterCalc" >&2
  exit 1
fi

APP_PATH="$(cd "$(dirname "$APP_PATH")" && pwd)/$(basename "$APP_PATH")"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/256x256/apps"
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
BIN_DIR="${HOME}/.local/bin"
DESKTOP_PATH="$APP_DIR/MonsterCalc.desktop"
ICON_PATH="$ICON_DIR/monstercalc.png"
LAUNCHER_PATH="$BIN_DIR/MonsterCalc"

mkdir -p "$ICON_DIR" "$APP_DIR" "$BIN_DIR"

install -m 0644 "$SCRIPT_DIR/MonsterApp.png" "$ICON_PATH"
install -m 0755 "$APP_PATH" "$LAUNCHER_PATH"

cat > "$DESKTOP_PATH" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=MonsterCalc
GenericName=Scratchpad Calculator
Comment=Live scratchpad calculator for math, units, programming, and EE work
Exec=$LAUNCHER_PATH
Icon=monstercalc
Terminal=false
Categories=Utility;Science;Engineering;Development;
Keywords=calculator;engineering;electronics;units;math;scratchpad;
StartupNotify=true
EOF

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor" >/dev/null 2>&1 || true
fi

echo "Installed MonsterCalc launcher:"
echo "  $DESKTOP_PATH"
echo
echo "Installed executable wrapper target:"
echo "  $LAUNCHER_PATH"
echo
echo "If your launcher does not appear immediately, log out and back in or refresh your desktop shell."
