def hex_to_rgb(text):
    value = text[1:] if text.startswith("#") else text
    if len(value) != 6 or any(ch not in "0123456789abcdefABCDEF" for ch in value):
        raise ValueError("expected six hex digits")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
