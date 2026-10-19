def rotate(values: list, steps: int) -> list:
    if not values:
        return []
    steps %= len(values)
    return values[-steps:] + values[:-steps] if steps else list(values)
