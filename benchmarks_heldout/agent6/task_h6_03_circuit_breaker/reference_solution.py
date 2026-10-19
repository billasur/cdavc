class CircuitBreaker:
    def __init__(self, failure_threshold, reset_timeout, half_open_successes=1):
        if failure_threshold < 1 or reset_timeout < 0 or half_open_successes < 1:
            raise ValueError("invalid configuration")
        self.threshold = failure_threshold
        self.timeout = reset_timeout
        self.needed = half_open_successes
        self._state = "closed"
        self._failures = 0
        self._successes = 0
        self._opened_at = 0.0

    def state(self, now):
        if self._state == "open" and now - self._opened_at >= self.timeout:
            self._state = "half_open"
            self._successes = 0
        return self._state

    def allow(self, now):
        return self.state(now) != "open"

    def record_success(self, now):
        current = self.state(now)
        if current == "closed":
            self._failures = 0
        elif current == "half_open":
            self._successes += 1
            if self._successes >= self.needed:
                self._state = "closed"
                self._failures = 0

    def record_failure(self, now):
        current = self.state(now)
        if current == "closed":
            self._failures += 1
            if self._failures >= self.threshold:
                self._state = "open"
                self._opened_at = now
        elif current == "half_open":
            self._state = "open"
            self._opened_at = now
