import math


def gcd_many(values: list[int]) -> int:
    if not values:
        raise ValueError("at least one value is required")
    result = 0
    for value in values:
        result = math.gcd(result, value)
    return result
