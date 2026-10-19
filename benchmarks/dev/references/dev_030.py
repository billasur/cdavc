def sort_records(records):
    return sorted(records, key=lambda record: (record.get("score", 0), record.get("name", "")))
