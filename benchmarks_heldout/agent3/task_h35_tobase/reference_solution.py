_DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


def to_base(n: int, base: int) -> str:
    if not 2 <= base <= 36:
        raise ValueError("base must be in 2..36")
    if n == 0:
        return "0"
    sign = "-" if n < 0 else ""
    n = abs(n)
    out = []
    while n:
        n, d = divmod(n, base)
        out.append(_DIGITS[d])
    return sign + "".join(reversed(out))
