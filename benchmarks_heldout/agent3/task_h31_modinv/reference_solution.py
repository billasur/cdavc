def mod_inverse(a: int, m: int) -> int:
    if m < 2:
        raise ValueError("modulus must be >= 2")
    old_r, r = a % m, m
    old_s, s = 1, 0
    while r:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_s, s = s, old_s - q * s
    if old_r != 1:
        raise ValueError("not invertible")
    return old_s % m
