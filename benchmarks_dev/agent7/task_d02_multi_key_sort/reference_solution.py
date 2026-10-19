"""Stable multi-key sort with missing fields."""


def sort_records(records, keys):
    result = list(records)
    for field, descending in reversed(list(keys)):
        if descending:
            result.sort(key=lambda r, f=field: (f in r, r[f] if f in r else 0), reverse=True)
        else:
            result.sort(key=lambda r, f=field: (f not in r, r[f] if f in r else 0))
    return result
