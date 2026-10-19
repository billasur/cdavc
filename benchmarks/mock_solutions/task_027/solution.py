def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:
    if not intervals:
        return []
    ordered = sorted((list(interval) for interval in intervals), key=lambda interval: interval[0])
    result = [ordered[0]]
    for start, end in ordered[1:]:
        if start <= result[-1][1]:
            result[-1][1] = max(result[-1][1], end)
        else:
            result.append([start, end])
    return result
