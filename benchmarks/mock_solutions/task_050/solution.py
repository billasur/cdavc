"""Render integers as comma separated ranges."""


def _piece(start: int, end: int) -> str:
    if end - start >= 2:
        return f"{start}-{end}"
    if end - start == 1:
        return f"{start},{end}"
    return str(start)


def compress_ranges(numbers: list[int]) -> str:
    if not numbers:
        return ""
    ordered = sorted(set(numbers))
    pieces: list[str] = []
    start = previous = ordered[0]
    for value in ordered[1:]:
        if value == previous + 1:
            previous = value
            continue
        pieces.append(_piece(start, previous))
        start = previous = value
    pieces.append(_piece(start, previous))
    return ",".join(pieces)
