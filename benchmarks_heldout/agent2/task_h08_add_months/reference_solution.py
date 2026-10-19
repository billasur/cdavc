import calendar
from datetime import date


def add_months(day: str, months: int) -> str:
    d = date.fromisoformat(day)
    index = d.year * 12 + (d.month - 1) + months
    year, month = divmod(index, 12)
    month += 1
    if not 1 <= year <= 9999:
        raise ValueError("year out of range")
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, last)).isoformat()
