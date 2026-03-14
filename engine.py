from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil, e, floor, log2, pi
from cmath import acos, asin, atan, cos, exp, log, log10, phase, polar, rect
from cmath import sin, sqrt, tan
from math import radians as rad
from math import degrees as deg
from typing import Any
import builtins
import io
import re
import tokenize

import keywords
from myfuncs import a2h, bin, bitget, bitpunch, cdf, eng_string, findrdiv, findres
from myfuncs import h2a, hex, mySum, pdf, rpar, vdiv


ANS_PREFIXES = ("<<", ">>", "+", "*", "^", "&", "/", "=", "%", "|")
ASSIGNMENT_RE = re.compile(r"^\s*(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<expr>.+?)\s*$")
CONVERSION_RE = re.compile(r"\s+to\s+")
SI_SUFFIX_PATTERNS = (
    (re.compile(r"((?<!\d)[.])"), "0."),
    (re.compile(r"(\d+[.,]?\d*)(p\b)"), r"(\g<1>*10**-12)"),
    (re.compile(r"(\d+[.,]?\d*)(n\b)"), r"(\g<1>*10**-9)"),
    (re.compile(r"(\d+[.,]?\d*)(u\b)"), r"(\g<1>*10**-6)"),
    (re.compile(r"(\d+[.,]?\d*)(m\b)"), r"(\g<1>*10**-3)"),
    (re.compile(r"(\d+[.,]?\d*)(k\b)"), r"(\g<1>*10**3)"),
    (re.compile(r"(\d+[.,]?\d*)(M\b)"), r"(\g<1>*10**6)"),
    (re.compile(r"(\d+[.,]?\d*)(G\b)"), r"(\g<1>*10**9)"),
)


@dataclass(slots=True)
class EngineConfig:
    sig_figs: int = 5
    res_format: str = "si"
    conv_xor_to_exp: bool = True


@dataclass(slots=True)
class LineEvaluation:
    source: str
    expression: str = ""
    value: Any = None
    display: str = ""
    error: str | None = None


@dataclass(slots=True)
class EvaluationState:
    variables: dict[str, Any] = field(default_factory=dict)
    ans: Any = None


class CalculationEngine:
    def __init__(self, config: EngineConfig | None = None):
        self.config = config or EngineConfig()

    def evaluate_document(self, text: str) -> list[LineEvaluation]:
        lines = text.split("\n")
        state = EvaluationState()
        evaluations: list[LineEvaluation] = []

        for line in lines:
            evaluation = self.evaluate_line(line, state)
            if evaluation.error is None and evaluation.display:
                state.ans = evaluation.value
            evaluations.append(evaluation)

        return evaluations

    def evaluate_line(
        self,
        line: str,
        state: EvaluationState | None = None,
    ) -> LineEvaluation:
        current_state = state or EvaluationState()
        clean_line = strip_inline_comment(line).strip()
        evaluation = LineEvaluation(source=line, expression=clean_line)

        if not clean_line:
            return evaluation

        assignment = ASSIGNMENT_RE.match(clean_line)
        if assignment:
            variable_name = assignment.group("name")
            expression = assignment.group("expr").strip()
            try:
                value = self._evaluate_expression(expression, current_state)
            except Exception as exc:  # noqa: BLE001 - preserve blank-on-error UX
                evaluation.error = str(exc)
                return evaluation

            current_state.variables[variable_name] = value
            evaluation.value = value
            evaluation.display = self._format_result(value, expression)
            return evaluation

        if CONVERSION_RE.search(clean_line):
            try:
                expression, unit = convert_units_expression(clean_line)
                value = self._evaluate_expression(expression, current_state)
            except Exception as exc:  # noqa: BLE001 - preserve blank-on-error UX
                evaluation.error = str(exc)
                return evaluation

            evaluation.expression = expression
            evaluation.value = value
            formatted = self._format_result(value)
            evaluation.display = f"{formatted} {unit}".rstrip()
            return evaluation

        try:
            value = self._evaluate_expression(clean_line, current_state)
        except Exception as exc:  # noqa: BLE001 - preserve blank-on-error UX
            evaluation.error = str(exc)
            return evaluation

        evaluation.value = value
        evaluation.display = self._format_result(value, clean_line)
        return evaluation

    def _evaluate_expression(self, expression: str, state: EvaluationState) -> Any:
        prepared = prepare_expression(
            expression,
            conv_xor_to_exp=self.config.conv_xor_to_exp,
            ans=state.ans,
        )

        namespace = build_eval_namespace()
        namespace.update(state.variables)
        namespace["ans"] = state.ans

        return eval(prepared, {"__builtins__": {}}, namespace)

    def _format_result(self, value: Any, expression: str = "") -> str:
        if value is None or callable(value):
            return ""
        bitpunch_base = bitpunch_display_base(expression)
        if bitpunch_base is not None:
            return builtins.hex(value) if bitpunch_base == "hex" else str(value)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return eng_string(value, self.config.sig_figs, "%s", self.config.res_format)
        return str(value)


def build_eval_namespace() -> dict[str, Any]:
    return {
        "abs": abs,
        "acos": acos,
        "a2h": a2h,
        "asin": asin,
        "atan": atan,
        "bin": bin,
        "bitget": bitget,
        "bitpunch": bitpunch,
        "cdf": cdf,
        "ceil": ceil,
        "cos": cos,
        "deg": deg,
        "e": e,
        "exp": exp,
        "findrdiv": findrdiv,
        "findres": findres,
        "floor": floor,
        "h2a": h2a,
        "hex": hex,
        "log": log,
        "log10": log10,
        "log2": log2,
        "max": max,
        "min": min,
        "pdf": pdf,
        "phase": phase,
        "pi": pi,
        "polar": polar,
        "rad": rad,
        "rect": rect,
        "rpar": rpar,
        "sin": sin,
        "sqrt": sqrt,
        "sum": mySum,
        "tan": tan,
        "vdiv": vdiv,
    }


def bitpunch_display_base(expression: str) -> str | None:
    first_arg = top_level_call_first_arg(expression, "bitpunch")
    if first_arg is None:
        return None

    normalized = first_arg.strip()
    if re.fullmatch(r"[+-]?\d[\d_]*", normalized):
        return "decimal"
    return "hex"


def top_level_call_first_arg(expression: str, function_name: str) -> str | None:
    prefix = f"{function_name}("
    stripped = expression.strip()
    if not stripped.startswith(prefix) or not stripped.endswith(")"):
        return None

    depth = 0
    arg_chars: list[str] = []
    for char in stripped[len(prefix) : -1]:
        if char == "," and depth == 0:
            return "".join(arg_chars).strip()
        if char == "(":
            depth += 1
        elif char == ")" and depth > 0:
            depth -= 1
        arg_chars.append(char)

    return "".join(arg_chars).strip() or None


def prepare_expression(expression: str, *, conv_xor_to_exp: bool, ans: Any) -> str:
    prepared = expression.strip()
    if not prepared:
        return prepared

    if any(prepared.startswith(prefix) for prefix in ANS_PREFIXES):
        prepared = f"ans{prepared}"

    for pattern, replacement in SI_SUFFIX_PATTERNS:
        prepared = pattern.sub(replacement, prepared)

    if conv_xor_to_exp:
        prepared = prepared.replace("^", "**")

    return prepared


def convert_units_expression(line: str) -> tuple[str, str]:
    parts = CONVERSION_RE.split(line, maxsplit=1)
    if len(parts) != 2:
        raise ValueError("Invalid conversion expression")

    conv_from, conv_to = parts
    new_unit = ""

    if (" C " in conv_from and conv_to.strip() == "F") or (
        conv_from.strip().endswith(" C") and conv_to.strip() == "F"
    ):
        conv_from = re.sub(r"\bC\b", "*1.8+32", conv_from)
        conv_to = re.sub(r"\bF\b", "", conv_to)
        return conv_from + conv_to, "F"

    if (" F " in conv_from and conv_to.strip() == "C") or (
        conv_from.strip().endswith(" F") and conv_to.strip() == "C"
    ):
        conv_from = re.sub(r"\bF\b", "/1.8-17.7777777778", conv_from)
        conv_to = re.sub(r"\bC\b", "", conv_to)
        return conv_from + conv_to, "C"

    for unit_type in keywords.unitsList:
        original_from = conv_from
        original_to = conv_to

        for unit, factor in unit_type.items():
            unit_pattern = rf"\b{re.escape(unit)}\b"
            replaced_from = re.sub(unit_pattern, f"*{factor}", conv_from)
            replaced_to = re.sub(unit_pattern, f"/{factor}", conv_to)
            if replaced_to != conv_to and not new_unit:
                new_unit = unit
            conv_from = replaced_from
            conv_to = replaced_to

        if conv_from != original_from and conv_to != original_to:
            return conv_from + conv_to, new_unit

        conv_from = original_from
        conv_to = original_to

    raise ValueError("Unsupported unit conversion")


def strip_inline_comment(line: str) -> str:
    try:
        tokens = tokenize.generate_tokens(io.StringIO(line).readline)
        parts: list[str] = []
        last_column = 0

        for token_type, token_text, _, (_, end_col), _ in tokens:
            if token_type == tokenize.COMMENT:
                break
            if token_type in (tokenize.ENDMARKER, tokenize.NEWLINE, tokenize.NL):
                continue
            if last_column < end_col - len(token_text):
                parts.append(" " * ((end_col - len(token_text)) - last_column))
            parts.append(token_text)
            last_column = end_col
    except tokenize.TokenError:
        # Live editing often produces incomplete expressions like "abs(".
        # In that state we preserve the raw line instead of crashing.
        return line.rstrip()

    return "".join(parts).rstrip()
