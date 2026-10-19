"""Sliding windows with step and partial tail."""


def windows(seq, size, step=1, keep_partial=False):
    if size < 1 or step < 1:
        raise ValueError("size and step must be >= 1")
    n = len(seq)
    out = []
    for i in range(0, n, step):
        if i + size <= n:
            out.append(list(seq[i:i + size]))
        elif keep_partial and (i == 0 or (i - step) + size < n):
            out.append(list(seq[i:i + size]))
    return out
