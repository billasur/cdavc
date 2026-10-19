def chunk(items: list, size: int) -> list[list]:
    if size <= 0:
        raise ValueError("size must be positive")
    return [items[index:index + size] for index in range(0, len(items), size)]
