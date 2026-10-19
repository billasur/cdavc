def pairwise_differences(values):
    return [values[index + 1] - values[index] for index in range(len(values) - 1)]
