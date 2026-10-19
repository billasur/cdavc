"""Convert a non-negative length between units."""

import math

_TO_METERS = {
    "mm": 0.001,
    "cm": 0.01,
    "m": 1.0,
    "km": 1000.0,
    "in": 0.0254,
    "ft": 0.3048,
}


def convert_length(value, from_unit: str, to_unit: str) -> float:
    for unit in (from_unit, to_unit):
        if not isinstance(unit, str):
            raise TypeError("units must be strings")
    from_key = from_unit.strip().lower()
    to_key = to_unit.strip().lower()
    for key in (from_key, to_key):
        if key not in _TO_METERS:
            raise ValueError(f"unknown unit: {key!r}")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("value must be a number")
    if not math.isfinite(value):
        raise ValueError("value must be finite")
    if value < 0:
        raise ValueError("value must not be negative")
    meters = value * _TO_METERS[from_key]
    return round(meters / _TO_METERS[to_key], 6)
