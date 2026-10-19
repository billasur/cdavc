"""Stable de-duplication with key function."""


def dedupe(items, key=None):
    seen = set()
    out = []
    for item in items:
        k = item if key is None else key(item)
        if k in seen:
            continue
        seen.add(k)
        out.append(item)
    return out
