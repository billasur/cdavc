def flatten_once(groups: list) -> list:
    result = []
    for group in groups:
        result.extend(group)
    return result
