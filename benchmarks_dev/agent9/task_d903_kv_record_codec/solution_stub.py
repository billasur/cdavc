"""One-line key=value record serialization with percent escaping."""


def dump_record(record: dict) -> str:
    raise NotImplementedError


def parse_record(text: str) -> dict:
    raise NotImplementedError
