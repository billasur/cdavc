import re

_RE = re.compile(r"^P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?$")


def parse_duration(text: str) -> float:
    m = _RE.match(text)
    if not m or not any(m.groups()):
        raise ValueError(f"invalid duration: {text!r}")
    if "T" in text and not any(m.group(i) for i in (3, 4, 5)):
        raise ValueError("T needs a time field")
    w, d, h, mi, s = (float(g) if g else 0.0 for g in m.groups())
    return float(w * 604800 + d * 86400 + h * 3600 + mi * 60 + s)
