def normalize_hex_color(text: str) -> str:
    s = text.strip()
    if not s.startswith("#"):
        raise ValueError("missing #")
    body = s[1:].lower()
    if len(body) not in (3, 6, 8) or any(c not in "0123456789abcdef" for c in body):
        raise ValueError("bad color")
    if len(body) == 3:
        body = "".join(c * 2 for c in body)
    if len(body) == 8 and body.endswith("ff"):
        body = body[:6]
    return "#" + body
