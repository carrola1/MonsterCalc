from __future__ import annotations

from myfuncs import bitpunch, cdf, eng_string, findres, pdf


def test_findres_handles_sub_10_ohm_values():
    assert findres(2.6, 1) == 2.62


def test_probability_helpers_use_stable_math():
    assert round(pdf(0), 6) == 0.398942
    assert round(cdf(0), 3) == 0.5


def test_eng_string_formats_supported_modes():
    assert eng_string(10000, 5, resFormat="scientific") == "1.0000e4"
    assert eng_string(10000, 5, resFormat="engineering") == "10e3"
    assert eng_string(10000, 5, resFormat="si") == "10k"


def test_bitpunch_sets_and_clears_bits():
    assert bitpunch(0x01, 7, 1) == 0x81
    assert bitpunch(0x81, 7, 0) == 0x01
