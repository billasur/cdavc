class TokenBucket:
    def __init__(self, capacity, refill_per_sec):
        if capacity <= 0 or refill_per_sec < 0:
            raise ValueError("invalid bucket")
        self.capacity = capacity
        self.rate = refill_per_sec
        self.tokens = float(capacity)
        self.last = None

    def allow(self, now, cost=1):
        if cost <= 0:
            raise ValueError("cost must be positive")
        if self.last is not None and now > self.last:
            self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
        if self.last is None or now > self.last:
            self.last = now
        if cost > self.capacity or cost > self.tokens:
            return False
        self.tokens -= cost
        return True
