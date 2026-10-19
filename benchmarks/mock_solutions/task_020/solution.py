def fibonacci(index: int) -> int:
    if index < 0:
        raise ValueError("index must be non-negative")
    previous, current = 0, 1
    for _ in range(index):
        previous, current = current, previous + current
    return previous
