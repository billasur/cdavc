def camel_to_snake(name):
    if not isinstance(name, str):
        raise TypeError("name must be a str")
    out = []
    n = len(name)
    for i, c in enumerate(name):
        if c.isupper() and i > 0:
            p = name[i - 1]
            nxt = name[i + 1] if i + 1 < n else ""
            if p != "_" and (p.islower() or p.isdigit() or (p.isupper() and nxt.islower())):
                out.append("_")
        out.append(c.lower())
    return "".join(out)


def snake_to_camel(name, upper_first=False):
    if not isinstance(name, str):
        raise TypeError("name must be a str")
    out = []
    for i, part in enumerate(p for p in name.split("_") if p):
        part = part.lower()
        out.append(part if (i == 0 and not upper_first) else part[:1].upper() + part[1:])
    return "".join(out)
