def dot_product(a, b):
    if len(a) != len(b):
        raise ValueError("vectors must have the same length")
    return sum(left * right for left, right in zip(a, b))
