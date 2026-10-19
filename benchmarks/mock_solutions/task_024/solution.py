def transpose(matrix: list[list]) -> list[list]:
    if not matrix:
        return []
    width = len(matrix[0])
    if any(len(row) != width for row in matrix):
        raise ValueError("matrix must be rectangular")
    return [[matrix[row][column] for row in range(len(matrix))] for column in range(width)]
