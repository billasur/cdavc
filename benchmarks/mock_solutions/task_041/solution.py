"""Compare two dotted numeric versions."""


def _components(version: str) -> list[int]:
    numbers: list[int] = []
    for piece in version.split("."):
        if not piece.isdigit():
            raise ValueError(f"invalid version component: {piece!r}")
        numbers.append(int(piece))
    return numbers


def compare_versions(left: str, right: str) -> int:
    first = _components(left)
    second = _components(right)
    width = max(len(first), len(second))
    first += [0] * (width - len(first))
    second += [0] * (width - len(second))
    if first < second:
        return -1
    if first > second:
        return 1
    return 0
