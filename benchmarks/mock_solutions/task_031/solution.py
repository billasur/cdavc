"""Parse a minimal INI document."""


def parse_ini(text: str) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    current: dict[str, str] | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line[0] in "#;":
            continue
        if line.startswith("[") and line.endswith("]"):
            name = line[1:-1].strip()
            if not name:
                raise ValueError("empty section name")
            current = sections.setdefault(name, {})
            continue
        if current is None:
            raise ValueError(f"key outside any section: {line!r}")
        if "=" not in line:
            raise ValueError(f"malformed line: {line!r}")
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            raise ValueError(f"empty key in line: {line!r}")
        current[key] = value.strip()
    return sections
