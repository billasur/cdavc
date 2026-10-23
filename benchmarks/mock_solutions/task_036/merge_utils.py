"""List merging helpers."""


def merge_lists(left: list, right: list) -> list:
    merged: list = []
    for value in list(left) + list(right):
        if value not in merged:
            merged.append(value)
    return merged
