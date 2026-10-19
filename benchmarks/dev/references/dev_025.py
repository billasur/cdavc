def drop_while_negative(values):
    index = 0
    while index < len(values) and values[index] < 0:
        index += 1
    return list(values[index:])
