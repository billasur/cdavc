def second_largest(values):
    if len(values) < 2:
        return None
    return sorted(values)[-2]
