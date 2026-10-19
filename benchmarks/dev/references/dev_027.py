def count_by_name(records):
    counts = {}
    for record in records:
        name = record.get("name")
        if name is None:
            continue
        counts[name] = counts.get(name, 0) + 1
    return counts
