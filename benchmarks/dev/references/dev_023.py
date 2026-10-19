def interleave(a, b):
    result = []
    for index in range(max(len(a), len(b))):
        if index < len(a):
            result.append(a[index])
        if index < len(b):
            result.append(b[index])
    return result
