"""core/cache.py - small, dependency-free response cache.

WHY THIS EXISTS
    Several of the assistant's one-shot calls are expensive and deterministic
    enough to repeat: a screenshot that has not changed, a document summary for
    a file whose mtime has not moved, a web search for the same query. Re-running
    them wastes quota and seconds.

    Two tiers, like the memory system: a hot in-process dict for the current
    session, and a JSON file on disk so a restart does not throw the work away.
    TTL per entry; expired entries are dropped lazily on read and eagerly on
    save. Nothing here knows about Gemini or any specific feature �?" callers
    pass a namespace and a key and get back whatever they stored.

    Thread-safe: the file is read once at first use and rewritten under a lock.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Optional

_BASE = Path(__file__).resolve().parent.parent
_CACHE_FILE = _BASE / "memory" / "cache.json"
_LOCK = threading.RLock()
_MEM: dict[str, dict] = {}   # key -> {"value":..., "expires": float}
_LOADED = False


def _now() -> float:
    return time.time()


def _load() -> None:
    global _LOADED
    if _LOADED:
        return
    with _LOCK:
        if _LOADED:
            return
        try:
            if _CACHE_FILE.exists():
                data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    for k, v in data.items():
                        if isinstance(v, dict) and "expires" in v:
                            if v["expires"] > _now():
                                _MEM[k] = v
        except Exception:
            pass
        _LOADED = True


def _save() -> None:
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with _LOCK:
            live = {k: v for k, v in _MEM.items() if v.get("expires", 0) > _now()}
            _CACHE_FILE.write_text(json.dumps(live, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _key(namespace: str, key: Any) -> str:
    raw = json.dumps({"ns": namespace, "k": key}, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get(namespace: str, key: Any) -> Optional[Any]:
    _load()
    k = _key(namespace, key)
    with _LOCK:
        entry = _MEM.get(k)
        if entry is None:
            return None
        if entry.get("expires", 0) <= _now():
            _MEM.pop(k, None)
            return None
        return entry.get("value")


def set(namespace: str, key: Any, value: Any, ttl: float = 300.0) -> None:
    _load()
    k = _key(namespace, key)
    with _LOCK:
        _MEM[k] = {"value": value, "expires": _now() + max(1.0, ttl), "ns": namespace}
    # persist lazily but cheaply
    try:
        _save()
    except Exception:
        pass


def invalidate(namespace: str = "", key: Any = None) -> int:
    _load()
    removed = 0
    with _LOCK:
        if key is None and not namespace:
            removed = len(_MEM)
            _MEM.clear()
        elif key is None:
            to_del = [k for k, v in _MEM.items() if v.get("ns") == namespace]
            for k in to_del:
                _MEM.pop(k, None)
                removed += 1
        else:
            k = _key(namespace, key)
            if k in _MEM:
                _MEM.pop(k, None)
                removed = 1
    _save()
    return removed


def clear() -> int:
    return invalidate()


def cached(namespace: str, ttl: float = 300.0):
    """Decorator for functions whose result depends only on their arguments."""
    def deco(fn):
        def wrapper(*args, **kwargs):
            key = {"args": args, "kwargs": kwargs}
            hit = get(namespace, key)
            if hit is not None:
                return hit
            result = fn(*args, **kwargs)
            set(namespace, key, result, ttl=ttl)
            return result
        wrapper.__name__ = getattr(fn, "__name__", "cached")
        wrapper.__wrapped__ = fn
        return wrapper
    return deco


def stats() -> dict:
    _load()
    with _LOCK:
        live = {k: v for k, v in _MEM.items() if v.get("expires", 0) > _now()}
    by_ns: dict[str, int] = {}
    for v in live.values():
        by_ns[v.get("ns", "?")] = by_ns.get(v.get("ns", "?"), 0) + 1
    return {"entries": len(live), "by_namespace": by_ns, "file": str(_CACHE_FILE)}
