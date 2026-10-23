"""Split one CSV record."""


def parse_csv_line(line: str) -> list[str]:
    fields: list[str] = []
    field: list[str] = []
    quoted = False
    in_quotes = False
    index = 0
    while index < len(line):
        character = line[index]
        if in_quotes:
            if character == '"':
                if index + 1 < len(line) and line[index + 1] == '"':
                    field.append('"')
                    index += 2
                    continue
                in_quotes = False
                index += 1
                continue
            field.append(character)
            index += 1
            continue
        if character == ",":
            fields.append("".join(field).strip() if not quoted else "".join(field))
            field = []
            quoted = False
            index += 1
            continue
        if character == '"' and not "".join(field).strip():
            field = []
            quoted = True
            in_quotes = True
            index += 1
            continue
        field.append(character)
        index += 1
    if in_quotes:
        raise ValueError(f"unterminated quoted field: {line!r}")
    fields.append("".join(field).strip() if not quoted else "".join(field))
    return fields
