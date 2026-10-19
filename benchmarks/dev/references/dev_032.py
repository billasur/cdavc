def bucket_counts(values, width):
    if not values:
        return []
    buckets = [0] * (max(values) // width + 1)
    for value in values:
        buckets[value // width] += 1
    return buckets
