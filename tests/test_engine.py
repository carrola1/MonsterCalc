from __future__ import annotations

from engine import CalculationEngine, convert_units_expression, strip_inline_comment


def test_engine_supports_assignments_and_ans():
    engine = CalculationEngine()
    results = engine.evaluate_document("x = 300\ny = 10k\nz = 50\ntot = x*z\nans + 5")

    assert [line.display for line in results] == ["300", "10k", "50", "15k", "15.005k"]


def test_engine_supports_line_number_references():
    engine = CalculationEngine()
    results = engine.evaluate_document("10\n20\nline1 + line2")

    assert [line.display for line in results] == ["10", "20", "30"]


def test_engine_supports_unit_conversions():
    engine = CalculationEngine()
    results = engine.evaluate_document("50 mm to in\n70 kg to lbs\n70 F to C\n1 KB to bits")

    assert [line.display for line in results] == [
        "1.9685 in",
        "154.32 lbs",
        "21.111 C",
        "8.192k bits",
    ]


def test_engine_treats_percent_as_suffix_and_mod_as_function():
    engine = CalculationEngine()
    results = engine.evaluate_document("50%\n200 * 10%\nmod(5, 2)")

    assert [line.display for line in results] == ["500m", "20", "1"]


def test_engine_supports_biset_programming_helper():
    engine = CalculationEngine()
    results = engine.evaluate_document("biset(0x01, 7, 1)\nbiset(1, 7, 1)")

    assert [line.display for line in results] == ["0x81", "129"]


def test_engine_supports_bitset_programming_alias():
    engine = CalculationEngine()
    results = engine.evaluate_document("bitset(0x01, 7, 1)\nbitset(1, 7, 1)")

    assert [line.display for line in results] == ["0x81", "129"]


def test_engine_preserves_hash_inside_strings_and_ignores_comments():
    engine = CalculationEngine()
    results = engine.evaluate_document('a2h("te#st") # inline comment')

    assert results[0].display == "b'7465237374'"


def test_engine_preserves_percent_inside_strings():
    engine = CalculationEngine()
    results = engine.evaluate_document('a2h("50%")')

    assert results[0].display == "b'353025'"


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


def test_engine_supports_new_ee_helpers():
    engine = CalculationEngine()
    results = engine.evaluate_document(
        "\n".join(
            [
                "findv(0.002, 4.7k)",
                "findi(5, 10k)",
                "findr(5, 0.002)",
                "xc(1k, 0.1u)",
                "xl(1k, 10m)",
                "db(2, 1)",
                "db10(10, 1)",
                "fc_rc(10k, 0.1u)",
                "tau(10k, 0.1u)",
                "rc_charge(5, 1m, 1k, 1u)",
                "rc_discharge(5, 1m, 1k, 1u)",
                "ledr(5, 2, 20m)",
                "adc(1.65, 3.3, 10)",
                "dac(512, 3.3, 10)",
            ]
        )
    )

    assert results[0].display == "9.4"
    assert results[1].display == "500u"
    assert results[2].display == "2.5k"
    assert results[3].display == "1.5915k"
    assert results[4].display == "62.832"
    assert results[5].display == "6.0206"
    assert results[6].display == "10"
    assert results[7].display == "159.15"
    assert results[8].display == "1m"
    assert results[9].display == "3.1606"
    assert results[10].display == "1.8394"
    assert results[11].display == "150"
    assert results[12].display == "512"
    assert results[13].display == "1.6516"


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
