"""Check the response of the actual quantized coefficients shipped in firmware.

This is a numerical filter check, not a substitute for on-device audio tests.
"""
from pathlib import Path
import cmath
import json
import math
import re

root = Path(__file__).resolve().parents[1]
source = (root / "components/mic_48_to_16/fir_coefficients.h").read_text()
body = source.split("FIR_COEFFICIENTS[FIR_TAPS] = {", 1)[1].split("}", 1)[0]
coefficients = [int(value) for value in re.findall(r"-?\d+", body)]
assert len(coefficients) == 63
assert coefficients == coefficients[::-1]
assert sum(coefficients) == 32768


def response_db(frequency):
    response = sum(value / 32768 * cmath.exp(-2j * math.pi * frequency * k / 48000)
                   for k, value in enumerate(coefficients))
    return 20 * math.log10(max(abs(response), 1e-12))


passband_error = max(abs(response_db(f)) for f in range(0, 5001, 100))
stopband_peak = max(response_db(f) for f in range(8000, 24001, 50))
assert passband_error < 0.1
assert stopband_peak < -40
result = {"passband_max_abs_db": passband_error, "stopband_peak_db": stopband_peak,
          "frequencies_db": {f: response_db(f) for f in (0, 1000, 5000, 8000, 12000, 16000)}}
print(json.dumps(result, indent=2))
