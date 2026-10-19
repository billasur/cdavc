def prime_factorization(n: int) -> list[tuple[int, int]]:
    if n < 2:
        raise ValueError("n must be >= 2")
    out: list[tuple[int, int]] = []
    p = 2
    while p * p <= n:
        if n % p == 0:
            e = 0
            while n % p == 0:
                n //= p
                e += 1
            out.append((p, e))
        p += 1 if p == 2 else 2
    if n > 1:
        out.append((n, 1))
    return out
