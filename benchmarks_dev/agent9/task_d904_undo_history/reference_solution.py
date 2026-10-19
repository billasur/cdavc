"""Undo/redo history over two lists."""


def _check(hist):
    if (
        not isinstance(hist, dict)
        or not isinstance(hist.get("past"), list)
        or not isinstance(hist.get("future"), list)
    ):
        raise TypeError("hist must be a dict with 'past' and 'future' lists")


def new_history() -> dict:
    return {"past": [], "future": []}


def push(hist: dict, value) -> None:
    _check(hist)
    hist["past"].append(value)
    hist["future"].clear()


def undo(hist: dict):
    _check(hist)
    if not hist["past"]:
        return None
    value = hist["past"].pop()
    hist["future"].append(value)
    return value


def redo(hist: dict):
    _check(hist)
    if not hist["future"]:
        return None
    value = hist["future"].pop()
    hist["past"].append(value)
    return value


def current(hist: dict):
    _check(hist)
    if not hist["past"]:
        return None
    return hist["past"][-1]
