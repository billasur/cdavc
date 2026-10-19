import math


def lcm_many(values: list[int]) -> int:
    if not values:
        raise ValueError("at least one value is required")
    result = 1
    for value in values:
        result = math.lcm(result, value)
    return result
