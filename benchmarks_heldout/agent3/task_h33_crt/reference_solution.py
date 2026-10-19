from math import gcd


def solve_congruences(pairs: list[tuple[int, int]]) -> tuple[int, int] | None:
    x, step = 0, 1
    for r, mod in pairs:
        if mod < 1:
            raise ValueError("modulus must be >= 1")
        r %= mod
        g = gcd(step, mod)
        if (r - x) % g:
            return None
        # solve step * t == r - x (mod mod)
        m2 = mod // g
        t = 0 if m2 == 1 else ((r - x) // g * pow(step // g, -1, m2)) % m2
        x += step * t
        step *= m2
        x %= step
    return x, step
