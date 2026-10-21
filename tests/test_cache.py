import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.cache import set, get, invalidate, stats


def test_set_get():
    set("t", "k", "v", ttl=10)
    assert get("t", "k") == "v"


def test_invalidate():
    set("t", "k2", "v2", ttl=10)
    invalidate("t", "k2")
    assert get("t", "k2") is None


def test_stats():
    s = stats()
    assert "entries" in s
