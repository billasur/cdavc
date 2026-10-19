from urllib.parse import parse_qsl


def parse_query(query: str) -> dict[str, list[str]]:
    result = {}
    for key, value in parse_qsl(query, keep_blank_values=True):
        result.setdefault(key, []).append(value)
    return result
