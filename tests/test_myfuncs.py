from __future__ import annotations

from myfuncs import adc, bitpunch, cdf, dac, db, db10, eng_string, fc_rc, findi
from myfuncs import findr, findres, findv, ledr, pdf, rc_charge, rc_discharge
from myfuncs import tau, xc, xl


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


def test_ee_helpers_cover_new_desktop_port():
    assert findv(0.002, 4700) == 9.4
    assert findi(5, 10000) == 0.0005
    assert findr(5, 0.002) == 2500
    assert round(xc(1000, 0.1e-6), 3) == 1591.549
    assert round(xl(1000, 10e-3), 4) == 62.8319
    assert round(db(2, 1), 4) == 6.0206
    assert db10(10, 1) == 10
    assert round(fc_rc(10000, 0.1e-6), 4) == 159.1549
    assert tau(10000, 0.1e-6) == 0.001
    assert round(rc_charge(5, 1e-3, 1000, 1e-6), 4) == 3.1606
    assert round(rc_discharge(5, 1e-3, 1000, 1e-6), 4) == 1.8394
    assert ledr(5, 2, 0.02) == 150
    assert adc(1.65, 3.3, 10) == 512
    assert round(dac(512, 3.3, 10), 4) == 1.6516
