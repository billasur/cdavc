"""Parse 'host:port' text into a (host, port) tuple."""


def parse_host_port(text: str) -> tuple:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    text = text.strip()
    if not text:
        raise ValueError("empty input")
    if text.count(":") != 1:
        raise ValueError("expected exactly one ':' separator")
    host, _, port_text = text.partition(":")
    host = host.strip()
    port_text = port_text.strip()
    if not host:
        raise ValueError("host must not be empty")
    if not port_text or not port_text.isdigit():
        raise ValueError("port must be a decimal integer")
    port = int(port_text)
    if not 1 <= port <= 65535:
        raise ValueError("port out of range 1..65535")
    return (host, port)
