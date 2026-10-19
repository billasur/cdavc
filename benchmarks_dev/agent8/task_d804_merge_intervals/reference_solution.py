"""Merge overlapping or touching [start, end] intervals."""

import math


def merge_intervals(intervals: list) -> list:
    if not isinstance(intervals, list):
        raise TypeError("intervals must be a list")
    pairs = []
    for pair in intervals:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise TypeError("each interval must be a pair")
        start, end = pair
        for endpoint in (start, end):
            if isinstance(endpoint, bool) or not isinstance(endpoint, (int, float)):
                raise TypeError("endpoints must be numbers")
            if not math.isfinite(endpoint):
                raise ValueError("endpoints must be finite")
        if start > end:
            raise ValueError("interval start must not exceed its end")
        pairs.append((start, end))
    pairs.sort()
    merged = []
    for start, end in pairs:
        if merged and start <= merged[-1][1]:
            if end > merged[-1][1]:
                merged[-1][1] = end
        else:
            merged.append([start, end])
    return merged
