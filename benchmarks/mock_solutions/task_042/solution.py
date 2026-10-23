"""Division helpers that tolerate a zero denominator."""


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    if denominator == 0:
        return float(default)
    return numerator / denominator


def percentage(part: float, whole: float) -> float:
    if whole == 0:
        return 0.0
    return round(part / whole * 100.0, 1)
