"""Rectangle area helpers."""


def total_area(rects: list[dict]) -> float:
    return sum(rect["w"] * rect["h"] for rect in rects)


def overlap_area(first: dict, second: dict) -> float:
    left = max(first["x"], second["x"])
    top = max(first["y"], second["y"])
    right = min(first["x"] + first["w"], second["x"] + second["w"])
    bottom = min(first["y"] + first["h"], second["y"] + second["h"])
    if right <= left or bottom <= top:
        return 0
    return (right - left) * (bottom - top)
