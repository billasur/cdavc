def snake_to_camel(text):
    parts = [part for part in text.split("_") if part]
    if not parts:
        return ""
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])
