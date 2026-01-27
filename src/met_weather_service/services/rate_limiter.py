from __future__ import annotations

import threading
import time
from collections import deque


class SlidingWindowRateLimiter:
    """
    Simple per-process sliding-window limiter.

    allow() returns True if action is allowed now, otherwise False.
    """
    def __init__(self, max_calls: int, period_s: float) -> None:
        self._max_calls = max_calls
        self._period_s = period_s
        self._lock = threading.Lock()
        self._events: deque[float] = deque()

    def allow(self) -> bool:
        now = time.monotonic()
        cutoff = now - self._period_s

        with self._lock:
            while self._events and self._events[0] <= cutoff:
                self._events.popleft()

            if len(self._events) >= self._max_calls:
                return False

            self._events.append(now)
            return True
