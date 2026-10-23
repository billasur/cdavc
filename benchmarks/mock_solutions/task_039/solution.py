"""Parse a compact duration into seconds."""

import re

_UNIT_SECONDS = {"d": 86400, "h": 3600, "m": 60, "s": 1}
_TOKEN = re.compile(r"\s*(\d+)\s*([dhms])")


def parse_duration(text: str) -> int:
    lowered = text.strip().lower()
    if not lowered:
        raise ValueError("empty duration")
    total = 0
    seen: set[str] = set()
    position = 0
    while position < len(lowered):
        match = _TOKEN.match(lowered, position)
        if match is None:
            raise ValueError(f"cannot parse duration near {lowered[position:]!r}")
        unit = match.group(2)
        if unit in seen:
            raise ValueError(f"duplicate unit: {unit!r}")
        seen.add(unit)
        total += int(match.group(1)) * _UNIT_SECONDS[unit]
        position = match.end()
    return total
