"""Compare dotted version strings numerically, padding with zeros."""


def _split(version: str) -> list:
    if not version:
        raise ValueError("empty version string")
    components = version.split(".")
    numbers = []
    for component in components:
        if not component or not component.isdigit():
            raise ValueError(f"invalid version component: {component!r}")
        numbers.append(int(component))
    return numbers


def compare_versions(a: str, b: str) -> int:
    left = _split(a)
    right = _split(b)
    width = max(len(left), len(right))
    left.extend([0] * (width - len(left)))
    right.extend([0] * (width - len(right)))
    for x, y in zip(left, right):
        if x < y:
            return -1
        if x > y:
            return 1
    return 0
