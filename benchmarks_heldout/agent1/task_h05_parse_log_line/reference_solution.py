"""Parse 'YYYY-MM-DD HH:MM:SS [LEVEL] message' log lines strictly."""

import datetime

_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def _valid_date(text: str) -> bool:
    if len(text) != 10 or text[4] != "-" or text[7] != "-":
        return False
    digits = text[:4] + text[5:7] + text[8:]
    if not digits.isdigit():
        return False
    try:
        datetime.date(int(text[:4]), int(text[5:7]), int(text[8:]))
    except ValueError:
        return False
    return True


def _valid_time(text: str) -> bool:
    if len(text) != 8 or text[2] != ":" or text[5] != ":":
        return False
    digits = text[:2] + text[3:5] + text[6:]
    if not digits.isdigit():
        return False
    hours, minutes, seconds = int(text[:2]), int(text[3:5]), int(text[6:])
    return hours < 24 and minutes < 60 and seconds < 60


def parse_log_line(line: str) -> dict:
    text = line.strip()
    parts = text.split(" ", 3)
    if len(parts) != 4:
        raise ValueError("expected 'YYYY-MM-DD HH:MM:SS [LEVEL] message'")
    date_text, time_text, level_text, message = parts
    if not _valid_date(date_text):
        raise ValueError(f"invalid date: {date_text!r}")
    if not _valid_time(time_text):
        raise ValueError(f"invalid time: {time_text!r}")
    if not (level_text.startswith("[") and level_text.endswith("]")):
        raise ValueError(f"invalid level field: {level_text!r}")
    level = level_text[1:-1]
    if level not in _LEVELS:
        raise ValueError(f"unknown level: {level!r}")
    if not message:
        raise ValueError("empty message")
    return {"date": date_text, "time": time_text, "level": level, "message": message}
