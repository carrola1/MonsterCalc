from __future__ import annotations

from calc import build_hover_previews, find_inline_completion, token_at_column
from engine import LineEvaluation
from toolButtons import TOKEN_SIGNATURES


def test_find_inline_completion_requires_unique_match():
    completion = find_inline_completion("bitg", 4, TOKEN_SIGNATURES)

    assert completion is not None
    assert completion.token == "bitget"
    assert completion.ghost_text == "et(value, msb, lsb)"
    assert completion.insert_text == "et"


def test_find_inline_completion_shows_signature_for_exact_function_name():
    completion = find_inline_completion("bin", 3, TOKEN_SIGNATURES)

    assert completion is not None
    assert completion.token == "bin"
    assert completion.ghost_text == "(value)"
    assert completion.insert_text == "("


def test_find_inline_completion_keeps_hint_after_open_parenthesis():
    completion = find_inline_completion("bin(", 4, TOKEN_SIGNATURES)

    assert completion is not None
    assert completion.token == "bin"
    assert completion.ghost_text == "value)"
    assert completion.insert_text == ""


def test_find_inline_completion_advances_to_next_empty_argument():
    completion = find_inline_completion("vdiv(5, ", 8, TOKEN_SIGNATURES)

    assert completion is not None
    assert completion.token == "vdiv"
    assert completion.ghost_text == "R1, R2)"
    assert completion.insert_text == ""


def test_find_inline_completion_stays_visible_while_typing_argument():
    completion = find_inline_completion("vdiv(5, 10", 10, TOKEN_SIGNATURES)

    assert completion is not None
    assert completion.token == "vdiv"
    assert completion.ghost_text == ", R2)"
    assert completion.insert_text == ""


def test_find_inline_completion_skips_current_argument_once_typing_starts():
    completion = find_inline_completion("vdiv(5", 6, TOKEN_SIGNATURES)

    assert completion is not None
    assert completion.token == "vdiv"
    assert completion.ghost_text == ", R1, R2)"
    assert completion.insert_text == ""


def test_find_inline_completion_ignores_short_or_ambiguous_fragments():
    assert find_inline_completion("bi", 2, TOKEN_SIGNATURES) is None
    assert find_inline_completion("bit", 3, TOKEN_SIGNATURES) is None
    assert find_inline_completion("log", 3, TOKEN_SIGNATURES) is None


def test_token_at_column_finds_variable_and_line_refs():
    assert token_at_column("line12 + total", 2) == "line12"
    assert token_at_column("line12 + total", 10) == "total"
    assert token_at_column("line12 + total", 7) is None


def test_build_hover_previews_uses_display_values():
    previews = build_hover_previews(
        [
            LineEvaluation(source="x = 10", display="10", assignment_name="x"),
            LineEvaluation(source="20", display="20"),
        ]
    )

    assert previews["x"] == "x = 10"
    assert previews["line1"] == "line1 = 10"
    assert previews["line2"] == "line2 = 20"
