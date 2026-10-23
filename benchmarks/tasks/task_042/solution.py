"""Division helpers that tolerate a zero denominator."""


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Return numerator divided by denominator, or default."""
    raise NotImplementedError

def percentage(part: float, whole: float) -> float:
    """Return the rounded percentage."""
    raise NotImplementedError
