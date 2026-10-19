def parse_ipv4(text: str) -> tuple[int, int, int, int] | None:
    parts = text.split(".")
    if len(parts) != 4:
        return None
    out = []
    for p in parts:
        if not p or any(c not in "0123456789" for c in p):
            return None
        if len(p) > 1 and p[0] == "0":
            return None
        n = int(p)
        if n > 255:
            return None
        out.append(n)
    return tuple(out)
