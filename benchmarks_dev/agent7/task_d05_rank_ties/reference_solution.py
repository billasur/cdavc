"""Rank scores with tie handling."""


def rank(scores, method="min"):
    if method not in ("min", "dense", "average"):
        raise ValueError(f"unknown method: {method!r}")
    values = list(scores)
    for v in values:
        if v != v:
            raise ValueError("NaN score")
    distinct = sorted(set(values), reverse=True)
    position = {}
    start = 1
    for d, v in enumerate(distinct, start=1):
        count = values.count(v)
        if method == "min":
            position[v] = start
        elif method == "dense":
            position[v] = d
        else:
            position[v] = start + (count - 1) / 2
        start += count
    return [position[v] for v in values]
