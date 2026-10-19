def take_while_positive(values):
    result = []
    for value in values:
        if value <= 0:
            break
        result.append(value)
    return result
