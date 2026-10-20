def _num(t, lo, hi):
    if not t.isascii() or not t.isdigit():
        raise ValueError("bad number")
    v = int(t)
    if not lo <= v <= hi:
        raise ValueError("out of range")
    return v


def expand_field(spec, lo, hi):
    if not isinstance(spec, str):
        raise TypeError("spec must be a str")
    if spec == "":
        raise ValueError("empty spec")
    out = set()
    for item in spec.split(","):
        if item == "":
            raise ValueError("empty item")
        base, sep, step_s = item.partition("/")
        step = None
        if sep:
            if not step_s.isascii() or not step_s.isdigit() or int(step_s) < 1:
                raise ValueError("bad step")
            step = int(step_s)
        if base == "*":
            a, b = lo, hi
        elif "-" in base:
            x, _, y = base.partition("-")
            a, b = _num(x, lo, hi), _num(y, lo, hi)
            if a > b:
                raise ValueError("reversed range")
        else:
            a = _num(base, lo, hi)
            b = a if step is None else hi
        out.update(range(a, b + 1, step or 1))
    return sorted(out)
