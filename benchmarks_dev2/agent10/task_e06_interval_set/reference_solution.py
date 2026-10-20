class IntervalSet:
    def __init__(self):
        self._iv = []

    @staticmethod
    def _check(a, b):
        for v in (a, b):
            if isinstance(v, bool) or not isinstance(v, int):
                raise TypeError("ints required")
        if a > b:
            raise ValueError("start > end")

    def add(self, start, end):
        self._check(start, end)
        if start == end:
            return None
        out = []
        s, e = start, end
        for a, b in self._iv:
            if b < s or a > e:
                out.append((a, b))
            else:
                s, e = min(s, a), max(e, b)
        out.append((s, e))
        out.sort()
        self._iv = out
        return None

    def remove(self, start, end):
        self._check(start, end)
        if start == end:
            return None
        out = []
        for a, b in self._iv:
            if b <= start or a >= end:
                out.append((a, b))
                continue
            if a < start:
                out.append((a, start))
            if b > end:
                out.append((end, b))
        self._iv = out
        return None

    def contains(self, x):
        if isinstance(x, bool) or not isinstance(x, int):
            raise TypeError("x must be an int")
        return any(a <= x < b for a, b in self._iv)

    def total(self):
        return sum(b - a for a, b in self._iv)

    def intervals(self):
        return list(self._iv)
