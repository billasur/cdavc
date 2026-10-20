def format_bytes(n, binary=False):
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an int")
    if n < 0:
        raise ValueError("n must be >= 0")
    base = 1024 if binary else 1000
    units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"] if binary else ["B", "kB", "MB", "GB", "TB", "PB"]
    if n < base:
        return f"{n} B"
    k = 1
    while k < 5 and n >= base ** (k + 1):
        k += 1

    def tenths(k):
        d = base ** k
        return (n * 20 + d) // (2 * d)

    t = tenths(k)
    if t >= base * 10 and k < 5:
        k += 1
        t = tenths(k)
    return f"{t // 10}.{t % 10} {units[k]}"
