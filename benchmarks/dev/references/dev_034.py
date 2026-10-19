def int_to_binary(n):
    if n < 0:
        raise ValueError("negative values have no binary form here")
    return format(n, "b")
