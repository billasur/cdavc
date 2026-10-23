"""Normalise a POSIX style path."""


def normalize_path(path: str) -> str:
    absolute = path.startswith("/")
    parts: list[str] = []
    for part in path.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts and parts[-1] != "..":
                parts.pop()
            elif not absolute:
                parts.append("..")
            continue
        parts.append(part)
    joined = "/".join(parts)
    if absolute:
        return "/" + joined
    return joined or "."
