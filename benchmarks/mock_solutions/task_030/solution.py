def stable_sort_records(records: list[dict], key: str) -> list[dict]:
    return sorted(records, key=lambda record: record[key])
