"""Integer conversion between bases 2 and 36."""

_DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


def _check_base(base):
    if isinstance(base, bool) or not isinstance(base, int):
        raise TypeError("base must be int")
    if not 2 <= base <= 36:
        raise ValueError("base must be in 2..36")


def to_base(number: int, base: int) -> str:
    if isinstance(number, bool) or not isinstance(number, int):
        raise TypeError("number must be int")
    if number < 0:
        raise ValueError("number must be >= 0")
    _check_base(base)
    if number == 0:
        return "0"
    out = []
    while number:
        number, rem = divmod(number, base)
        out.append(_DIGITS[rem])
    return "".join(reversed(out))


def from_base(text: str, base: int) -> int:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    _check_base(base)
    digits = text.strip().lower()
    if not digits:
        raise ValueError("empty text")
    value = 0
    for ch in digits:
        digit = _DIGITS.find(ch)
        if digit == -1 or digit >= base:
            raise ValueError(f"invalid digit {ch!r} for base {base}")
        value = value * base + digit
    return value
