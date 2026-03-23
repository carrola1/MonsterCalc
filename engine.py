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
from myfuncs import a2h, adc, bin, biset, bitget, bitpunch, bitset, cdf, dac, db, db10, eng_string
from myfuncs import fc_rc, findi, findr, findrdiv, findres, findv, h2a, hex, ledr
from myfuncs import mod, mySum, pdf, rc_charge, rc_discharge, rpar, tau, vdiv, xc, xl


ANS_PREFIXES = ("<<", ">>", "+", "*", "^", "&", "/", "=", "|")
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


@dataclass
class EngineConfig:
    sig_figs: int = 5
    res_format: str = "si"
    conv_xor_to_exp: bool = True


@dataclass
class LineEvaluation:
    source: str
    expression: str = ""
    value: Any = None
    display: str = ""
    error: str | None = None
    assignment_name: str | None = None


@dataclass
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

        for line_number, line in enumerate(lines, start=1):
            evaluation = self.evaluate_line(line, state)
            if evaluation.error is None and evaluation.display:
                state.ans = evaluation.value
            if self._stores_line_reference(evaluation):
                state.variables[f"line{line_number}"] = evaluation.value
            evaluations.append(evaluation)

        return evaluations

    def _stores_line_reference(self, evaluation: LineEvaluation) -> bool:
        return (
            evaluation.error is None
            and evaluation.value is not None
            and not callable(evaluation.value)
        )

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
            evaluation.assignment_name = variable_name
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
        biset_base = biset_display_base(expression)
        if biset_base is not None:
            return builtins.hex(value) if biset_base == "hex" else str(value)
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
        "biset": biset,
        "bitget": bitget,
        "bitpunch": bitpunch,
        "bitset": bitset,
        "cdf": cdf,
        "ceil": ceil,
        "cos": cos,
        "dac": dac,
        "db": db,
        "db10": db10,
        "deg": deg,
        "e": e,
        "exp": exp,
        "fc_rc": fc_rc,
        "findi": findi,
        "findr": findr,
        "findrdiv": findrdiv,
        "findres": findres,
        "findv": findv,
        "floor": floor,
        "h2a": h2a,
        "hex": hex,
        "ledr": ledr,
        "log": log,
        "log10": log10,
        "log2": log2,
        "max": max,
        "min": min,
        "mod": mod,
        "pdf": pdf,
        "phase": phase,
        "pi": pi,
        "polar": polar,
        "rad": rad,
        "rc_charge": rc_charge,
        "rc_discharge": rc_discharge,
        "rect": rect,
        "rpar": rpar,
        "sin": sin,
        "sqrt": sqrt,
        "sum": mySum,
        "tan": tan,
        "tau": tau,
        "vdiv": vdiv,
        "xc": xc,
        "xl": xl,
        "adc": adc,
    }


def biset_display_base(expression: str) -> str | None:
    first_arg = None
    for function_name in ("biset", "bitset", "bitpunch"):
        first_arg = top_level_call_first_arg(expression, function_name)
        if first_arg is not None:
            break
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

    prepared = rewrite_percent_suffixes(prepared)

    if conv_xor_to_exp:
        prepared = prepared.replace("^", "**")

    return prepared


def rewrite_percent_suffixes(expression: str) -> str:
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(expression).readline))
    except tokenize.TokenError:
        return expression

    ignored_types = {
        tokenize.NL,
        tokenize.NEWLINE,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.ENDMARKER,
    }
    meaningful_indices = [
        index
        for index, token_info in enumerate(tokens)
        if token_info.type not in ignored_types
    ]

    rewritten: list[tuple[int, str]] = []
    for position, token_index in enumerate(meaningful_indices):
        token_info = tokens[token_index]
        if token_info.type == tokenize.OP and token_info.string == "%":
            previous = tokens[meaningful_indices[position - 1]] if position > 0 else None
            following = (
                tokens[meaningful_indices[position + 1]]
                if position + 1 < len(meaningful_indices)
                else None
            )

            previous_is_value = previous is not None and (
                previous.type in (tokenize.NUMBER, tokenize.NAME, tokenize.STRING)
                or previous.string == ")"
            )
            following_is_postfix_compatible = following is None or (
                following.type == tokenize.OP
                and following.string in {"+", "-", "*", "/", "^", "&", "|", ",", ")", "<<", ">>", "="}
            ) or (
                following.type == tokenize.NAME and following.string == "to"
            )

            if previous_is_value and following_is_postfix_compatible:
                rewritten.append((token_info.type, "/100"))
                continue
            raise ValueError("Use % as a percent suffix and mod(x, y) for modulus")

        rewritten.append((token_info.type, token_info.string))

    return tokenize.untokenize(rewritten)


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
