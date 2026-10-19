def cumulative_sum(values):
    totals = []
    running = 0
    for value in values:
        running += value
        totals.append(running)
    return totals
