"""Intersect two sorted interval lists."""


def intersect_intervals(first: list[list[int]], second: list[list[int]]) -> list[list[int]]:
    result: list[list[int]] = []
    left = right = 0
    while left < len(first) and right < len(second):
        low = max(first[left][0], second[right][0])
        high = min(first[left][1], second[right][1])
        if low <= high:
            result.append([low, high])
        if first[left][1] < second[right][1]:
            left += 1
        else:
            right += 1
    return result
