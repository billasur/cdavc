"""Parse one CSV line with quoted fields (strict RFC-4180-style rules)."""


def parse_csv_line(line: str) -> list:
    fields = []
    index = 0
    length = len(line)
    while True:
        if index < length and line[index] == '"':
            index += 1
            chars = []
            while True:
                if index >= length:
                    raise ValueError("unterminated quoted field")
                if line[index] == '"':
                    if index + 1 < length and line[index + 1] == '"':
                        chars.append('"')
                        index += 2
                    else:
                        index += 1
                        break
                else:
                    chars.append(line[index])
                    index += 1
            if index < length and line[index] != ",":
                raise ValueError("unexpected character after closing quote")
            fields.append("".join(chars))
        else:
            start = index
            while index < length and line[index] != ",":
                index += 1
            field = line[start:index]
            if '"' in field:
                raise ValueError("double quote inside unquoted field")
            fields.append(field)
        if index >= length:
            break
        index += 1  # consume the comma
        if index >= length:
            fields.append("")
            break
    return fields
