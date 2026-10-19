def top_k_frequent(values: list, k: int) -> list:
    if k <= 0:
        return []
    counts = {}
    first_seen = {}
    for index, value in enumerate(values):
        counts[value] = counts.get(value, 0) + 1
        first_seen.setdefault(value, index)
    return sorted(counts, key=lambda value: (-counts[value], first_seen[value]))[:k]
