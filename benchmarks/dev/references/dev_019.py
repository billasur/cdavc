def normalize_vector(values):
    norm = sum(value * value for value in values) ** 0.5
    if norm == 0:
        return [0.0 for _ in values]
    return [round(value / norm, 6) for value in values]
