"""Interval set."""


class IntervalSet:
    def add(self, start, end):
        raise NotImplementedError

    def remove(self, start, end):
        raise NotImplementedError

    def contains(self, x):
        raise NotImplementedError

    def total(self):
        raise NotImplementedError

    def intervals(self):
        raise NotImplementedError
