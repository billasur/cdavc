def _mins(t: str) -> int:
    if not isinstance(t, str) or len(t) != 5 or t[2] != ":" or not (t[:2] + t[3:]).isdigit():
        raise ValueError(f"bad time: {t!r}")
    h, m = int(t[:2]), int(t[3:])
    if h > 23 or m > 59:
        raise ValueError(f"bad time: {t!r}")
    return h * 60 + m


def _fmt(n: int) -> str:
    return f"{n // 60:02d}:{n % 60:02d}"


def free_slots(busy, day_start: str, day_end: str) -> list:
    lo, hi = _mins(day_start), _mins(day_end)
    if hi <= lo:
        raise ValueError("empty window")
    spans = []
    for s, e in busy:
        a, b = _mins(s), _mins(e)
        if b < a:
            raise ValueError("busy end before start")
        spans.append((a, b))
    spans.sort()
    out = []
    cursor = lo
    for a, b in spans:
        if a > cursor:
            out.append((cursor, min(a, hi)))
        cursor = max(cursor, b)
        if cursor >= hi:
            break
    if cursor < hi:
        out.append((cursor, hi))
    return [(_fmt(a), _fmt(b)) for a, b in out if b > a]
