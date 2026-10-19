def reorder(packets, start=0):
    pending = {}
    for seq, payload in packets:
        if seq < start or seq in pending:
            continue
        pending[seq] = payload
    delivered = []
    nxt = start
    while nxt in pending:
        delivered.append(pending.pop(nxt))
        nxt += 1
    return delivered, sorted(pending)
