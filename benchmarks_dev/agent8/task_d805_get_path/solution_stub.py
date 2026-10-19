"""Look up a dotted path in nested dicts."""

_MISSING = object()


def get_path(data: dict, path: str, default=_MISSING):
    raise NotImplementedError
