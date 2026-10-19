def filter_by_score(records, minimum):
    return [record for record in records if record.get("score", 0) >= minimum]
