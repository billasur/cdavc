"""One-line key=value record serialization with percent escaping."""

_ESCAPES = {"%": "%25", "=": "%3D", ";": "%3B"}


def _escape(part: str) -> str:
    out = []
    for ch in part:
        out.append(_ESCAPES.get(ch, ch))
    return "".join(out)


def _unescape(part: str) -> str:
    out = []
    i = 0
    while i < len(part):
        ch = part[i]
        if ch != "%":
            out.append(ch)
            i += 1
            continue
        hexpart = part[i + 1 : i + 3]
        if len(hexpart) != 2 or any(c not in "0123456789ABCDEF" for c in hexpart):
            raise ValueError(f"bad escape: %{hexpart}")
        out.append(chr(int(hexpart, 16)))
        i += 3
    return "".join(out)


def dump_record(record: dict) -> str:
    if not isinstance(record, dict):
        raise TypeError("record must be dict")
    for key, value in record.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise TypeError("keys and values must be str")
    return ";".join(f"{_escape(key)}={_escape(record[key])}" for key in sorted(record))


def parse_record(text: str) -> dict:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    record = {}
    if text == "":
        return record
    for entry in text.split(";"):
        if "=" not in entry:
            raise ValueError(f"entry without '=': {entry!r}")
        raw_key, _, raw_value = entry.partition("=")
        key = _unescape(raw_key)
        if key in record:
            raise ValueError(f"duplicate key: {key!r}")
        record[key] = _unescape(raw_value)
    return record
