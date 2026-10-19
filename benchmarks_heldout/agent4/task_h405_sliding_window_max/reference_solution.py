"""Maximum of each contiguous window of length k."""

from collections import deque


def sliding_window_max(values: list[int], k: int) -> list[int]:
    if k < 1:
        raise ValueError("k must be at least 1")
    result: list[int] = []
    window: deque[int] = deque()
    for index, value in enumerate(values):
        while window and window[0] <= index - k:
            window.popleft()
        while window and values[window[-1]] <= value:
            window.pop()
        window.append(index)
        if index >= k - 1:
            result.append(values[window[0]])
    return result
