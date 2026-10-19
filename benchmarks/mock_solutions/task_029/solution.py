def format_duration(seconds: int) -> str:
    if seconds < 0:
        raise ValueError("seconds must be non-negative")
    if seconds == 0:
        return "0s"
    values = []
    for amount, suffix in ((86400, "d"), (3600, "h"), (60, "m"), (1, "s")):
        count, seconds = divmod(seconds, amount)
        if count:
            values.append(f"{count}{suffix}")
    return " ".join(values)
