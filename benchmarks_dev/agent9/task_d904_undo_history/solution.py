"""Undo/redo history over two lists."""


def new_history() -> dict:
    raise NotImplementedError


def push(hist: dict, value) -> None:
    raise NotImplementedError


def undo(hist: dict):
    raise NotImplementedError


def redo(hist: dict):
    raise NotImplementedError


def current(hist: dict):
    raise NotImplementedError
