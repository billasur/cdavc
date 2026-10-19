from datetime import date, timedelta


def business_days(start: str, end: str, holidays=()) -> int:
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    if e < s:
        raise ValueError("end before start")
    hol = {date.fromisoformat(h) for h in holidays}
    count = 0
    d = s
    while d < e:
        if d.weekday() < 5 and d not in hol:
            count += 1
        d += timedelta(days=1)
    return count
