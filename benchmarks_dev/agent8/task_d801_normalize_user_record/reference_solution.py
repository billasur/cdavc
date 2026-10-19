"""Validate and normalize a user record dict."""


def normalize_user_record(record: dict) -> dict:
    if not isinstance(record, dict):
        raise TypeError("record must be a dict")
    for key in ("name", "email", "age"):
        if key not in record:
            raise KeyError(f"missing required key: {key}")
    name = record["name"]
    if not isinstance(name, str):
        raise TypeError("name must be a string")
    name = name.strip()
    if not name:
        raise ValueError("name must not be empty")
    email = record["email"]
    if not isinstance(email, str):
        raise TypeError("email must be a string")
    email = email.strip().lower()
    if email.count("@") != 1:
        raise ValueError("email must contain exactly one '@'")
    local, _, domain = email.partition("@")
    if not local:
        raise ValueError("email local part must not be empty")
    if not domain or "." not in domain:
        raise ValueError("email domain must contain a dot")
    age = record["age"]
    if isinstance(age, bool) or not isinstance(age, int):
        raise TypeError("age must be an int")
    if not 0 <= age <= 150:
        raise ValueError("age out of range 0..150")
    tags = record.get("tags", [])
    if not isinstance(tags, list):
        raise TypeError("tags must be a list of strings")
    seen = set()
    norm_tags = []
    for tag in tags:
        if not isinstance(tag, str):
            raise TypeError("each tag must be a string")
        tag = tag.strip()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        norm_tags.append(tag)
    return {"name": name, "email": email, "age": age, "tags": norm_tags}
