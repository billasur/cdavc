def mean(values):
    if not values:
        raise ValueError("mean of an empty list")
    return round(sum(values) / len(values), 6)
