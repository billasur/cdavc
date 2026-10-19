def matrix_multiply(left: list[list], right: list[list]) -> list[list]:
    if not left or not right:
        return []
    left_width = len(left[0])
    right_width = len(right[0])
    if any(len(row) != left_width for row in left) or any(len(row) != right_width for row in right):
        raise ValueError("matrices must be rectangular")
    if left_width != len(right):
        raise ValueError("matrices are incompatible")
    return [
        [sum(left[row][inner] * right[inner][column] for inner in range(left_width)) for column in range(right_width)]
        for row in range(len(left))
    ]
