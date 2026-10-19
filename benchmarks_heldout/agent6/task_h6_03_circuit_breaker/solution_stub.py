"""Circuit breaker state machine driven by caller-supplied time."""


class CircuitBreaker:
    def __init__(self, failure_threshold: int, reset_timeout: float, half_open_successes: int = 1) -> None:
        raise NotImplementedError

    def state(self, now: float) -> str:
        raise NotImplementedError

    def allow(self, now: float) -> bool:
        raise NotImplementedError

    def record_success(self, now: float) -> None:
        raise NotImplementedError

    def record_failure(self, now: float) -> None:
        raise NotImplementedError
