def variance_population(values):
    if not values:
        raise ValueError("variance of an empty list")
    average = sum(values) / len(values)
    return round(sum((value - average) ** 2 for value in values) / len(values), 6)
