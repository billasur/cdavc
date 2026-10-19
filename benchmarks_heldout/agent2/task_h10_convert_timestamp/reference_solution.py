import re
from datetime import datetime, timedelta, timezone

_TS = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(Z|[+-]\d{2}:\d{2})$")
_OFF = re.compile(r"^(Z|[+-]\d{2}:\d{2})$")


def _tz(text: str) -> timezone:
    if not _OFF.match(text):
        raise ValueError(f"bad offset: {text!r}")
    if text == "Z":
        return timezone.utc
    sign = 1 if text[0] == "+" else -1
    h, m = int(text[1:3]), int(text[4:6])
    if m > 59 or h > 23:
        raise ValueError(f"offset out of range: {text!r}")
    return timezone(sign * timedelta(hours=h, minutes=m))


def convert_timestamp(ts: str, offset: str) -> str:
    match = _TS.match(ts)
    if not match:
        raise ValueError(f"bad timestamp: {ts!r}")
    naive = datetime.strptime(match.group(1), "%Y-%m-%dT%H:%M:%S")
    moment = naive.replace(tzinfo=_tz(match.group(2)))
    out = moment.astimezone(_tz(offset))
    text = out.strftime("%Y-%m-%dT%H:%M:%S%z")
    return text[:-2] + ":" + text[-2:]
