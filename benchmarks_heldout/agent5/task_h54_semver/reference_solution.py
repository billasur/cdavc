import re

_CORE = r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
_PRE = r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
_BUILD = r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
_RE = re.compile(_CORE + _PRE + _BUILD)


def _parse(text: str):
    m = _RE.fullmatch(text)
    if m is None:
        raise ValueError(text)
    core = tuple(int(m.group(i)) for i in (1, 2, 3))
    pre = m.group(4).split(".") if m.group(4) is not None else None
    if pre is not None:
        for ident in pre:
            if ident.isdigit() and len(ident) > 1 and ident[0] == "0":
                raise ValueError(text)
    return core, pre


def _cmp(x, y):
    return (x > y) - (x < y)


def compare_semver(a: str, b: str) -> int:
    ca, pa = _parse(a)
    cb, pb = _parse(b)
    if ca != cb:
        return _cmp(ca, cb)
    if pa is None and pb is None:
        return 0
    if pa is None:
        return 1
    if pb is None:
        return -1
    for x, y in zip(pa, pb):
        xn, yn = x.isdigit(), y.isdigit()
        if xn and yn:
            if int(x) != int(y):
                return _cmp(int(x), int(y))
        elif xn != yn:
            return -1 if xn else 1
        elif x != y:
            return _cmp(x, y)
    return _cmp(len(pa), len(pb))
