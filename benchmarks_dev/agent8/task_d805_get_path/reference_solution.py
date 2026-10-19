"""Look up a dotted path in nested dicts."""

_MISSING = object()


def get_path(data: dict, path: str, default=_MISSING):
    if not isinstance(data, dict):
        raise TypeError("data must be a dict")
    if not isinstance(path, str):
        raise TypeError("path must be a string")
    if path == "":
        raise ValueError("path must not be empty")
    segments = path.split(".")
    if any(segment == "" for segment in segments):
        raise ValueError("path segments must not be empty")
    current = data
    for segment in segments:
        if not isinstance(current, dict):
            raise TypeError(f"cannot traverse into non-dict at segment {segment!r}")
        if segment not in current:
            if default is _MISSING:
                raise KeyError(segment)
            return default
        current = current[segment]
    return current
