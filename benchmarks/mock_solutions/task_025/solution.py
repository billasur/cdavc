def spiral_order(matrix: list[list]) -> list:
    if not matrix:
        return []
    if any(len(row) != len(matrix[0]) for row in matrix):
        raise ValueError("matrix must be rectangular")
    top, bottom = 0, len(matrix) - 1
    left, right = 0, len(matrix[0]) - 1
    result = []
    while top <= bottom and left <= right:
        result.extend(matrix[top][left:right + 1])
        top += 1
        for row in range(top, bottom + 1):
            result.append(matrix[row][right])
        right -= 1
        if top <= bottom:
            result.extend(reversed(matrix[bottom][left:right + 1]))
            bottom -= 1
        if left <= right:
            for row in range(bottom, top - 1, -1):
                result.append(matrix[row][left])
            left += 1
    return result
