from __future__ import annotations

from binascii import hexlify, unhexlify
import math
import builtins

from resistors import res1Per, resp1Per


SI_EXPONENTS = {
    -24: "y",
    -21: "z",
    -18: "a",
    -15: "f",
    -12: "p",
    -9: "n",
    -6: "u",
    -3: "m",
    3: "k",
    6: "M",
    9: "G",
    12: "T",
    15: "P",
    18: "E",
    21: "Z",
    24: "Y",
}


def bin(val, len=None):
    val = math.floor(val)
    if len is not None:
        return "0b" + f"{val:0{len}b}"
    return builtins.bin(val)


def hex(val, len=None):
    val = math.floor(val)
    if len is not None:
        return "0x" + f"{val:0{len}x}"
    return builtins.hex(val)


def mySum(*args):
    total = 0
    for arg in args:
        total += arg
    return total


def bitget(valIn, stopBit, startBit):
    mask = 0
    for ii in range(startBit, stopBit + 1):
        mask += 2**ii
    bitsRtn = (valIn & mask) >> startBit
    return bin(bitsRtn)


def a2h(dataIn):
    return hexlify(bytes(dataIn, "utf-8"))


def h2a(dataIn):
    return unhexlify("{0:0X}".format(dataIn))


def findres(target_r, tol=1):
    if target_r <= 0:
        raise ValueError("target resistance must be positive")

    resList = resp1Per if tol == 0.1 else res1Per
    normalized = target_r
    multiplier = 0

    while normalized >= 100:
        normalized /= 10
        multiplier += 1

    while normalized < 10:
        normalized *= 10
        multiplier -= 1

    closest_match = min(resList, key=lambda value: abs(value - normalized))
    return closest_match * 10**multiplier


def vdiv(vin, r1, r2):
    return vin * r2 / (r1 + r2)


def rpar(*argv):
    reciprocal_sum = 0
    for arg in argv:
        reciprocal_sum += 1 / arg
    return 1 / reciprocal_sum


def findrdiv(vin, vout, tol=1):
    if vin == 0:
        raise ValueError("vin must be non-zero")

    resistors = resp1Per if tol == 0.1 else res1Per
    resistor_decades = [1, 10, 100, 1000]
    resistorsBig = [value * scale for scale in resistor_decades for value in resistors]

    ratio = vout / vin
    matchR1 = 0
    matchR2 = 0
    bestDiff = float("inf")

    if ratio <= 0.5:
        for r2 in resistors:
            for r1 in reversed(resistorsBig):
                newRatio = r2 / (r1 + r2)
                diff = abs(newRatio - ratio)
                if diff < bestDiff:
                    bestDiff = diff
                    matchR1 = r1
                    matchR2 = r2
    else:
        for r2 in resistorsBig:
            for r1 in resistors:
                newRatio = r2 / (r1 + r2)
                diff = abs(newRatio - ratio)
                if diff < bestDiff:
                    bestDiff = diff
                    matchR1 = r1
                    matchR2 = r2

    return [matchR1, matchR2]


def pdf(std_dev):
    return math.exp(-0.5 * std_dev**2) / math.sqrt(2 * math.pi)


def cdf(std_dev):
    return 0.5 * (1 + math.erf(std_dev / math.sqrt(2)))


def eng_string(x, sigFigs, format="%s", resFormat="engineering"):
    if not math.isfinite(x):
        return str(x)

    if x == 0:
        return "0"

    if resFormat == "scientific":
        precision = max(sigFigs - 1, 0)
        mantissa, exponent = f"{x:.{precision}e}".split("e")
        return f"{mantissa}e{int(exponent)}"

    if resFormat in ("si", "engineering"):
        sign = "-" if x < 0 else ""
        x = abs(x)
        exp3 = int(math.floor(math.log10(x) / 3) * 3)
        x3 = x / (10**exp3)
        x3 = float(f"{x3:.{sigFigs}g}")

        if x3 >= 1000:
            x3 /= 1000
            exp3 += 3

        if resFormat == "si" and exp3 in SI_EXPONENTS:
            suffix = SI_EXPONENTS[exp3]
        elif exp3 == 0:
            suffix = ""
        else:
            suffix = f"e{exp3}"

        value = f"{x3:.{sigFigs}g}"
        return f"{sign}{value}{suffix}"

    return f"{x:.{sigFigs}g}"
