from __future__ import annotations

import re

from qt_compat import QAction, QMenu, QToolButton


FUNCTION_SECTIONS = [
    (
        "General Math",
        [
            ("floor", "Round down"),
            ("ceil", "Round up"),
            ("min", "Return list min"),
            ("max", "Return list max"),
            ("sum", "Return list sum"),
            ("sqrt", "Square root"),
            ("abs", "Absolute value"),
            ("log", "Log base e"),
            ("log10", "Log base 10"),
            ("log2", "Log base 2"),
            ("exp", "Exponential (e**x)"),
            ("phase", "Phase of complex #"),
            ("rect", "Complex polar to rect (mag, ang)"),
            ("polar", "Complex rect to polar"),
        ],
    ),
    (
        "Geometry",
        [
            ("sin", "Sine"),
            ("cos", "Cosine"),
            ("tan", "Tangent"),
            ("asin", "Arc-sine"),
            ("acos", "Arc-cosine"),
            ("atan", "Arc-tangent"),
            ("rad", "Convert deg to rad"),
            ("deg", "Convert rad to deg"),
        ],
    ),
    (
        "Probability",
        [
            ("cdf", "Normal cumulative distribution (std_dev)"),
            ("pdf", "Normal probability distribution (std_dev)"),
        ],
    ),
]

EE_SECTIONS = [
    (
        "Electrical",
        [
            ("findres", "Closest std value (target, tol)"),
            ("vdiv", "Calc voltage divider out (vin, R1, R2)"),
            ("rpar", "Parallel resistor calc (R1, R2, R3...)"),
            ("findrdiv", "Best R divider values (vin, vout, tol)"),
            ("findv", "Find voltage (current, resistance)"),
            ("findi", "Find current (voltage, resistance)"),
            ("findr", "Find resistance (voltage, current)"),
            ("xc", "Capacitive reactance (f, C)"),
            ("xl", "Inductive reactance (f, L)"),
            ("db", "Voltage ratio in dB (v1, v2)"),
            ("db10", "Power ratio in dB (p1, p2)"),
            ("fc_rc", "RC cutoff frequency (R, C)"),
            ("tau", "RC time constant (R, C)"),
            ("rc_charge", "RC charge voltage (vin, t, R, C)"),
            ("rc_discharge", "RC discharge voltage (v0, t, R, C)"),
            ("ledr", "LED series resistor (Vs, Vf, I)"),
            ("adc", "ADC code (vin, vref, bits)"),
            ("dac", "DAC voltage (code, vref, bits)"),
        ],
    ),
    (
        "Programming",
        [
            ("hex", "Convert to hex"),
            ("bin", "Convert to bin"),
            ("bitget", "Bit slice (value, msb, lsb)"),
            ("bitpunch", "Set/clear bit (value, bit, state)"),
            ("a2h", "Convert ASCII 'str' to hex"),
            ("h2a", "Convert hex to ASCII"),
        ],
    ),
]

SYMBOL_SECTIONS = [
    (
        "Misc",
        [
            ("ans", "Result from previous line"),
            ("to", "Unit conversion (ex. 5 mm to in)"),
        ],
    ),
    (
        "Math",
        [
            ("**", "Power (ex. 2**3 = 8)"),
            ("%", "Modulus (ex. 5 % 2 = 1)"),
            ("e", "Exponent (ex. 5e-3 = 0.005)"),
        ],
    ),
    (
        "Programming",
        [
            ("0x", "Hex (ex. 0x12 = 18)"),
            ("0b", "Binary (ex. 0b101 = 5)"),
            ("<<", "Shift left (ex. 2 << 2 = 8)"),
            (">>", "Shift right (ex. 8 >> 2 = 2)"),
            ("|", "Bitwise OR (ex. 8 | 1 = 9)"),
            ("&", "Bitwise AND (ex. 5 & 1 = 1)"),
            ("^", "Bitwise XOR (ex. 5 ^ 1 = 4)"),
        ],
    ),
    (
        "Scientific Notation",
        [
            ("p", "Pico (ex. 1p = 1e-12)"),
            ("n", "Nano (ex. 1n = 1e-9)"),
            ("u", "Micro (ex. 1u = 1e-6)"),
            ("m", "Milli (ex. 1m = 1e-3)"),
            ("k", "Kilo (ex. 1k = 1e3)"),
            ("M", "Mega (ex. 1M = 1e6)"),
            ("G", "Giga (ex. 1G = 1e9)"),
        ],
    ),
]

UNIT_SECTIONS = [
    (
        "Length",
        [
            ("mm", "Millimeters"),
            ("cm", "Centimeters"),
            ("m", "Meters"),
            ("km", "Kilometers"),
            ("mil", "Thousandths of an inch"),
            ("in", "Inches"),
        ],
    ),
    (
        "Volume",
        [
            ("mL", "Milliliter"),
            ("L", "Liter"),
            ("tsp", "Teaspoon"),
            ("tbl", "Tablespoon"),
            ("oz", "Fluid ounce"),
            ("pt", "Pint"),
            ("qt", "Quart"),
            ("gal", "Gallon"),
        ],
    ),
    (
        "Mass",
        [
            ("mg", "Milligram"),
            ("g", "Gram"),
            ("kg", "Kilogram"),
            ("oz", "Ounce"),
            ("lbs", "Pound"),
        ],
    ),
    (
        "Force",
        [
            ("N", "Newton"),
            ("kN", "Kilonewton"),
            ("lbf", "Pound force"),
        ],
    ),
    (
        "Temperature",
        [
            ("C", "Degrees Celsius"),
            ("F", "Degrees Fahrenheit"),
        ],
    ),
    (
        "Memory",
        [
            ("bits", "Bits"),
            ("bytes", "Bytes"),
            ("KB", "IEC KiB (1024 bytes)"),
            ("MB", "IEC MiB"),
            ("GB", "IEC GiB"),
            ("TB", "IEC TiB"),
            ("Kb", "Kilobits (1000 bits)"),
            ("Mb", "Megabits"),
            ("Gb", "Gigabits"),
            ("Tb", "Terabits"),
        ],
    ),
]


def _build_token_hints(
    section_groups: tuple[list[tuple[str, list[tuple[str, str]]]], ...],
) -> dict[str, str]:
    hints: dict[str, str] = {}
    for sections in section_groups:
        for _, entries in sections:
            for token, description in entries:
                hints.setdefault(token, description)
    return hints


TOKEN_HINTS = _build_token_hints(
    (FUNCTION_SECTIONS, EE_SECTIONS, SYMBOL_SECTIONS, UNIT_SECTIONS)
)


def _build_result_hints(hints: dict[str, str]) -> dict[str, str]:
    return {
        token: re.sub(r"\s*\([^)]*\)", "", description).strip()
        for token, description in hints.items()
    }


TOKEN_RESULT_HINTS = _build_result_hints(TOKEN_HINTS)

TOKEN_SIGNATURES = {
    "floor": "(value)",
    "ceil": "(value)",
    "min": "(value1, value2, ...)",
    "max": "(value1, value2, ...)",
    "sum": "(list)",
    "sqrt": "(value)",
    "abs": "(value)",
    "log": "(value)",
    "log10": "(value)",
    "log2": "(value)",
    "exp": "(value)",
    "phase": "(value)",
    "rect": "(mag, ang)",
    "polar": "(value)",
    "sin": "(angle)",
    "cos": "(angle)",
    "tan": "(angle)",
    "asin": "(value)",
    "acos": "(value)",
    "atan": "(value)",
    "rad": "(deg)",
    "deg": "(rad)",
    "cdf": "(std_dev)",
    "pdf": "(std_dev)",
    "findres": "(target, tol)",
    "vdiv": "(vin, R1, R2)",
    "rpar": "(R1, R2, R3...)",
    "findrdiv": "(vin, vout, tol)",
    "findv": "(current, resistance)",
    "findi": "(voltage, resistance)",
    "findr": "(voltage, current)",
    "xc": "(freq, cap)",
    "xl": "(freq, ind)",
    "db": "(value1, value2)",
    "db10": "(value1, value2)",
    "fc_rc": "(R, C)",
    "tau": "(R, C)",
    "rc_charge": "(vin, t, R, C)",
    "rc_discharge": "(v0, t, R, C)",
    "ledr": "(Vs, Vf, I)",
    "adc": "(vin, vref, bits)",
    "dac": "(code, vref, bits)",
    "hex": "(value)",
    "bin": "(value)",
    "bitget": "(value, msb, lsb)",
    "bitpunch": "(value, bit, state)",
    "a2h": "(text)",
    "h2a": "(hex_text)",
}


def _build_menu(tool_button: QToolButton, sections: list[tuple[str, list[tuple[str, str]]]]) -> QMenu:
    menu = QMenu(tool_button)
    for section_name, entries in sections:
        section_menu = menu.addMenu(section_name)
        for token, description in entries:
            action = QAction(f"{token}: {description}", section_menu)
            action.setData(token)
            action.setToolTip(description)
            section_menu.addAction(action)
    return menu


def populateFuncButton(funcTool: QToolButton):
    return _build_menu(funcTool, FUNCTION_SECTIONS)


def populateEEButton(eeTool: QToolButton):
    return _build_menu(eeTool, EE_SECTIONS)


def populateSymButton(symTool: QToolButton):
    return _build_menu(symTool, SYMBOL_SECTIONS)


def populateUnitButton(unitTool: QToolButton):
    return _build_menu(unitTool, UNIT_SECTIONS)
