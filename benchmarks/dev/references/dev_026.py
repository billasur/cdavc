def partition_parity(values):
    evens = [value for value in values if value % 2 == 0]
    odds = [value for value in values if value % 2 != 0]
    return (evens, odds)
