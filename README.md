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

## Notes

- The app keeps the original two-pane scratchpad workflow and menu structure.
- Project metadata now lives in `pyproject.toml`.
- Legacy build artifacts are still in the repository for reference, but the recommended development path is the editable install above.
