def rgb_to_hex(r, g, b):
    if any(not 0 <= channel <= 255 for channel in (r, g, b)):
        raise ValueError("channel outside 0..255")
    return "#{:02x}{:02x}{:02x}".format(r, g, b)
