"""core/telemetry.py - optional OpenTelemetry tracing, no-op when absent.

WHY THIS EXISTS
    Observability should never be a hard dependency. When opentelemetry is
    installed, spans are exported (OTLP if configured); otherwise every call
    is a no-op that costs a single attribute lookup. Instrumentation is added
    at call sites via `span()` context manager and `trace()` decorator.
"""
from __future__ import annotations

import os
from contextlib import contextmanager


def _enabled() -> bool:
    return os.environ.get("JARVIS_TELEMETRY", "").lower() in ("1", "true", "yes", "on")


_OTEL = None
if _enabled():
    try:
        from opentelemetry import trace as _otel_trace
        _OTEL = _otel_trace
    except Exception:
        _OTEL = None

_TRACER = _OTEL.get_tracer("jarvis") if _OTEL is not None else None


@contextmanager
def span(name: str, **attrs):
    if _TRACER is None:
        yield None
        return
    with _TRACER.start_as_current_span(name) as s:
        for k, v in attrs.items():
            try:
                s.set_attribute(k, v)
            except Exception:
                pass
        yield s


def trace(name: str):
    def deco(fn):
        def wrapper(*a, **kw):
            with span(name):
                return fn(*a, **kw)
        wrapper.__name__ = getattr(fn, "__name__", "traced")
        wrapper.__wrapped__ = fn
        return wrapper
    return deco


def is_enabled() -> bool:
    return _TRACER is not None
