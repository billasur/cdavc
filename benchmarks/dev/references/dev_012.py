def binomial(n, k):
    if k < 0 or k > n:
        return 0
    result = 1
    for step in range(k):
        result = result * (n - step) // (step + 1)
    return result
