"""Parse INI-style config text into nested dicts."""


def parse_config(text: str) -> dict:
    config = {}
    section = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        if line.startswith("["):
            if len(line) < 3 or not line.endswith("]"):
                raise ValueError(f"malformed section header: {raw_line!r}")
            name = line[1:-1].strip()
            if not name:
                raise ValueError(f"empty section name: {raw_line!r}")
            section = name
            config.setdefault(section, {})
            continue
        if "=" not in line:
            raise ValueError(f"expected 'key = value' line: {raw_line!r}")
        if section is None:
            raise ValueError(f"key/value line before any section: {raw_line!r}")
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            raise ValueError(f"empty key: {raw_line!r}")
        config[section][key] = value.strip()
    return config
