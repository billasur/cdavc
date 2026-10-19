def parse_ints(text):
    result = []
    for field in text.split(","):
        field = field.strip()
        if not field:
            continue
        result.append(int(field))
    return result
