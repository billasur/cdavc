"""Convert integers between bases 2 and 36."""

_DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


def to_base(value: int, base: int) -> str:
    if not 2 <= base <= 36:
        raise ValueError(f"base out of range: {base}")
    if value == 0:
        return "0"
    sign = "-" if value < 0 else ""
    remaining = abs(int(value))
    digits: list[str] = []
    while remaining:
        remaining, remainder = divmod(remaining, base)
        digits.append(_DIGITS[remainder])
    return sign + "".join(reversed(digits))


def from_base(text: str, base: int) -> int:
    if not 2 <= base <= 36:
        raise ValueError(f"base out of range: {base}")
    value = text.strip().lower()
    sign = 1
    if value.startswith("-"):
        sign = -1
        value = value[1:]
    if not value:
        raise ValueError("empty digit string")
    total = 0
    for character in value:
        if character not in _DIGITS:
            raise ValueError(f"invalid digit: {character!r}")
        digit = _DIGITS.index(character)
        if digit >= base:
            raise ValueError(f"digit {character!r} is out of range for base {base}")
        total = total * base + digit
    return sign * total
