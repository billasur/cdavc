def min_coins(coins, amount):
    if not isinstance(coins, (list, tuple)):
        raise TypeError("coins must be a list or tuple")
    for c in coins:
        if isinstance(c, bool) or not isinstance(c, int):
            raise TypeError("coins must be ints")
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise TypeError("amount must be an int")
    if any(c <= 0 for c in coins) or amount < 0:
        raise ValueError("bad value")
    cs = sorted(set(coins))
    best = [None] * (amount + 1)
    best[0] = []
    for a in range(1, amount + 1):
        cand = None
        for c in cs:
            if c <= a and best[a - c] is not None:
                t = sorted(best[a - c] + [c], reverse=True)
                key = (len(t), [-x for x in t])
                if cand is None or key < cand[0]:
                    cand = (key, t)
        best[a] = cand[1] if cand else None
    return best[amount]
