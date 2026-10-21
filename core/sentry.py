"""core/sentry.py - optional Sentry error tracking."""
from __future__ import annotations

import os


def init() -> bool:
    dsn = os.environ.get("SENTRY_DSN", "")
    if not dsn:
        return False
    try:
        import sentry_sdk
        sentry_sdk.init(dsn=dsn, traces_sample_rate=0.1)
        return True
    except ImportError:
        return False


def capture(exc: BaseException) -> None:
    try:
        import sentry_sdk
        sentry_sdk.capture_exception(exc)
    except Exception:
        pass
