"""core/profiler.py - simple performance profiler."""
from __future__ import annotations

import time
from contextlib import contextmanager


_TIMINGS: dict[str, list[float]] = {}


@contextmanager
def profile(name: str):
    t0 = time.perf_counter()
    yield
    dt = time.perf_counter() - t0
    _TIMINGS.setdefault(name, []).append(dt)


def stats() -> dict:
    out = {}
    for k, v in _TIMINGS.items():
        out[k] = {"count": len(v), "avg": sum(v) / len(v), "max": max(v), "min": min(v)}
    return out


def reset() -> None:
    _TIMINGS.clear()
