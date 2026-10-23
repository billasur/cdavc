"""Build a lowercase URL slug."""

import re

_SEPARATOR = re.compile(r"[^a-z0-9]+")


def slugify(title: str) -> str:
    ascii_only = "".join(character for character in title.lower() if ord(character) < 128)
    return _SEPARATOR.sub("-", ascii_only).strip("-")
