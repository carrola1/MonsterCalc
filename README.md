# MonsterCalc

MonsterCalc is a desktop scratchpad calculator for the kind of work that does not fit neatly into a single REPL or a traditional calculator. You type one expression per line, and results appear live in a synchronized pane beside the editor.

It is built for quick technical work:

- General math, trig, logs, and complex helpers
- Variable assignment with `ans` support
- Unit conversion with `to`
- Electronics helpers like `findres`, `rpar`, `vdiv`, and `findrdiv`
- Programming helpers like `bin`, `hex`, `bitget`, `a2h`, and `h2a`

## Modernized Runtime

The current codebase targets modern Python and Qt:

- Python `3.10+`
- `PySide6` as the default Qt binding
- `PyQt6` supported as a fallback by the compatibility layer

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python MonsterCalc.py
```

On Windows, activate the environment with:

```powershell
.venv\Scripts\activate
```

Then run:

```powershell
python MonsterCalc.py
```

## Tests

Run the core automated suite with:

```bash
pytest
```

That covers the calculator engine, formatting helpers, unit conversion, and regression cases around parsing and electrical helpers.

Optional Qt smoke tests are included but skipped by default because they require a local GUI-capable Qt runtime:

```bash
MONSTERCALC_RUN_QT_TESTS=1 pytest tests/test_widget.py
```

## Packaging

The recommended PyInstaller build path is the spec file:

```bash
pyinstaller MonsterCalc.spec
```

On macOS, that spec now builds a proper `MonsterCalc.app` bundle and uses the native `Monster.icns` dock icon.

If you prefer building directly from the source entrypoint, use the command for your platform.

macOS:

```bash
pyinstaller --noconfirm --windowed --name MonsterCalc --icon Monster.icns \
  --add-data "Monster.png:." \
  --add-data "MonsterHeader.png:." \
  --add-data "demo.txt:." \
  --add-data "release_notes.txt:." \
  --add-data "UserGuide.html:." \
  MonsterCalc.py
```

Linux:

```bash
pyinstaller --noconfirm --windowed --name MonsterCalc --icon Monster.ico \
  --add-data "Monster.png:." \
  --add-data "MonsterHeader.png:." \
  --add-data "demo.txt:." \
  --add-data "release_notes.txt:." \
  --add-data "UserGuide.html:." \
  MonsterCalc.py
```

Windows PowerShell:

```powershell
pyinstaller --noconfirm --windowed --name MonsterCalc --icon Monster.ico `
  --add-data "Monster.png;." `
  --add-data "MonsterHeader.png;." `
  --add-data "demo.txt;." `
  --add-data "release_notes.txt;." `
  --add-data "UserGuide.html;." `
  MonsterCalc.py
```

Windows should continue using `Monster.ico` for the icon.

### Linux Desktop Integration

Linux desktop environments usually show the right launcher/taskbar icon when MonsterCalc is installed through a `.desktop` entry rather than launched directly from the binary.

This repo includes:

- `MonsterCalc.desktop`: a generic launcher definition for packagers
- `install_linux.sh`: a user-local installer that copies the icon and writes a launcher into `~/.local/share/applications`

After building with PyInstaller, install the launcher with:

```bash
chmod +x install_linux.sh
./install_linux.sh ./dist/MonsterCalc
```

That installs:

- the executable into `~/.local/bin/MonsterCalc`
- the icon into `~/.local/share/icons/hicolor/256x256/apps/monstercalc.png`
- the launcher into `~/.local/share/applications/MonsterCalc.desktop`

## Notes

- The app keeps the original two-pane scratchpad workflow and menu structure.
- Project metadata now lives in `pyproject.toml`.
- Legacy build artifacts are still in the repository for reference, but the recommended development path is the editable install above.
