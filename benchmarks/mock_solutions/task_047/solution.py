"""Group a list of dictionaries by one key."""


def group_by(records: list[dict], key: str) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for record in records:
        if key not in record:
            raise KeyError(key)
        groups.setdefault(record[key], []).append(record)
    return groups
