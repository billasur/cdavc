"""Compute a trailing moving average."""


def moving_average(values: list[float], window: int) -> list[float]:
    if window < 1:
        raise ValueError("window must be at least 1")
    if len(values) < window:
        return []
    result = [round(sum(values[:window]) / window, 3)]
    running = sum(values[:window])
    for index in range(window, len(values)):
        running += values[index] - values[index - window]
        result.append(round(running / window, 3))
    return result
