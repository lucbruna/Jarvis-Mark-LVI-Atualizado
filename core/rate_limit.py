"""core/rate_limit.py - simple per-key rate limiter."""
from __future__ import annotations

import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, max_calls: int = 10, window_sec: float = 60.0):
        self.max_calls = max_calls
        self.window = window_sec
        self._calls: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str = "default") -> bool:
        now = time.monotonic()
        q = self._calls[key]
        while q and q[0] < now - self.window:
            q.popleft()
        if len(q) >= self.max_calls:
            return False
        q.append(now)
        return True


# Global limiter for API calls
api_limiter = RateLimiter(max_calls=30, window_sec=60.0)
