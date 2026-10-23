"""Convert a human readable size into bytes."""

import re

_UNITS = {"b": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3}
_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([A-Za-z]+)\s*$")


def parse_size(text: str) -> int:
    match = _PATTERN.match(text)
    if match is None:
        raise ValueError(f"cannot parse size: {text!r}")
    unit = match.group(2).lower()
    if unit not in _UNITS:
        raise ValueError(f"unknown unit: {match.group(2)!r}")
    return int(round(float(match.group(1)) * _UNITS[unit]))
