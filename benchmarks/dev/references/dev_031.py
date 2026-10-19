def pluck(records):
    return [record.get("name") for record in records]
