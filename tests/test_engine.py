from __future__ import annotations

from engine import CalculationEngine, convert_units_expression, strip_inline_comment


def test_engine_supports_assignments_and_ans():
    engine = CalculationEngine()
    results = engine.evaluate_document("x = 300\ny = 10k\nz = 50\ntot = x*z\nans + 5")

    assert [line.display for line in results] == ["300", "10k", "50", "15k", "15.005k"]


def test_engine_supports_unit_conversions():
    engine = CalculationEngine()
    results = engine.evaluate_document("50 mm to in\n70 kg to lbs\n70 F to C\n1 KB to bits")

    assert [line.display for line in results] == [
        "1.9685 in",
        "154.32 lbs",
        "21.111 C",
        "8.192k bits",
    ]


def test_engine_supports_bitpunch_programming_helper():
    engine = CalculationEngine()
    results = engine.evaluate_document("bitpunch(0x01, 7, 1)\nbitpunch(1, 7, 1)")

    assert [line.display for line in results] == ["0x81", "129"]


def test_engine_preserves_hash_inside_strings_and_ignores_comments():
    engine = CalculationEngine()
    results = engine.evaluate_document('a2h("te#st") # inline comment')

    assert results[0].display == "b'7465237374'"


def test_engine_keeps_blank_result_for_invalid_lines():
    engine = CalculationEngine()
    results = engine.evaluate_document("not valid\n2 + 2")

    assert results[0].display == ""
    assert results[0].error is not None
    assert results[1].display == "4"


def test_engine_suppresses_raw_callable_display():
    engine = CalculationEngine()
    result = engine.evaluate_document("bin")[0]

    assert result.display == ""
    assert result.error is None


def test_findrdiv_supports_extreme_ratios_after_fix():
    engine = CalculationEngine()
    result = engine.evaluate_document("findrdiv(5, 0.05, 1)")[0]

    assert result.display == "[1130.0, 11.5]"


def test_convert_units_expression_rewrites_supported_units():
    expression, unit = convert_units_expression("50 mm to in")

    assert expression == "50 *1/25.4"
    assert unit == "in"


def test_strip_inline_comment_ignores_hash_in_strings():
    assert strip_inline_comment('a2h("te#st") # keep string') == 'a2h("te#st")'


def test_strip_inline_comment_preserves_incomplete_expression():
    assert strip_inline_comment("abs(-") == "abs(-"


def test_engine_keeps_blank_result_for_incomplete_abs_expression():
    engine = CalculationEngine()
    results = engine.evaluate_document("abs(-\n2 + 2")

    assert results[0].display == ""
    assert results[0].error is not None
    assert results[1].display == "4"
