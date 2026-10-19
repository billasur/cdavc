def binary_search(values: list, target) -> int:
    left, right = 0, len(values) - 1
    result = -1
    while left <= right:
        middle = (left + right) // 2
        if values[middle] == target:
            result = middle
            right = middle - 1
        elif values[middle] < target:
            left = middle + 1
        else:
            right = middle - 1
    return result
