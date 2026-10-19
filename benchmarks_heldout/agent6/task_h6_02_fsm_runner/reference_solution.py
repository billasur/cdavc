def run_machine(transitions, start, events):
    known = set()
    for (state, _event), target in transitions.items():
        known.add(state)
        known.add(target)
    if start not in known:
        raise ValueError("unknown start state")
    state = start
    trace = []
    for event in events:
        state = transitions.get((state, event), state)
        trace.append(state)
    return state, trace
