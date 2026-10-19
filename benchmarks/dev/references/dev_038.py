def weekday_abbrev(name):
    days = {
        "monday": "Mon",
        "tuesday": "Tue",
        "wednesday": "Wed",
        "thursday": "Thu",
        "friday": "Fri",
        "saturday": "Sat",
        "sunday": "Sun",
    }
    try:
        return days[name.lower()]
    except KeyError:
        raise ValueError("not a weekday name") from None
