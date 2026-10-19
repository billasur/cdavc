"""Token-bucket rate limiter with caller-supplied time."""


class TokenBucket:
    def __init__(self, capacity: float, refill_per_sec: float) -> None:
        raise NotImplementedError

    def allow(self, now: float, cost: float = 1) -> bool:
        raise NotImplementedError
