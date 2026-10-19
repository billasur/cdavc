"""Merge half-open intervals."""


def merge_intervals(intervals):
    items = []
    for start, end in intervals:
        if start > end:
            raise ValueError(f"invalid interval: ({start!r}, {end!r})")
        if start < end:
            items.append((start, end))
    items.sort()
    out = []
    for start, end in items:
        if out and start <= out[-1][1]:
            if end > out[-1][1]:
                out[-1] = (out[-1][0], end)
        else:
            out.append((start, end))
    return out
