def schedule_jobs(durations, deps, workers):
    if workers < 1:
        raise ValueError("workers must be >= 1")
    for name, d in durations.items():
        if d <= 0:
            raise ValueError("durations must be positive")
    for name, ds in deps.items():
        if name not in durations:
            raise ValueError(f"unknown job {name}")
        for dep in ds:
            if dep not in durations:
                raise ValueError(f"unknown dependency {dep}")
    # cycle check
    state = {}
    def visit(n):
        if state.get(n) == 1:
            raise ValueError("cycle")
        if state.get(n) == 2:
            return
        state[n] = 1
        for dep in deps.get(n, []):
            visit(dep)
        state[n] = 2
    for n in sorted(durations):
        visit(n)
    schedule = {}
    running = {}
    done = set()
    t = 0
    while len(done) < len(durations):
        for n in [n for n, end in running.items() if end <= t]:
            done.add(n)
            del running[n]
        for n in sorted(durations):
            if len(running) >= workers:
                break
            if n in schedule:
                continue
            if all(d in done for d in deps.get(n, [])):
                schedule[n] = (t, t + durations[n])
                running[n] = t + durations[n]
        if len(done) + len(running) == len(durations) and not running:
            break
        if running:
            t = min(running.values())
    makespan = max((e for _, e in schedule.values()), default=0)
    return schedule, makespan
