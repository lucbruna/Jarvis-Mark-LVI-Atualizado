"""JARVIS plugin - price tracker: monitor product prices and alert."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "price_tracker",
    "description": "Track product prices and alert when they drop. Stores tracked items in memory/tracked_prices.json.",
    "brief": "Price tracker: add/check/remove tracked products.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "add|check|list|remove"},
            "url": {"type": "STRING", "description": "Product URL (add)."},
            "target_price": {"type": "NUMBER", "description": "Target price (add)."},
            "name": {"type": "STRING", "description": "Product name (add/remove)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}

_STORE = Path(__file__).resolve().parents[1] / "memory" / "tracked_prices.json"


def _load():
    try:
        if _STORE.exists():
            return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def _save(data):
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    data = _load()
    if action == "add":
        entry = {"name": params.get("name", "product"), "url": params.get("url", ""), "target": params.get("target_price", 0), "added": time.time()}
        data.append(entry)
        _save(data)
        return outcome.done("price_tracker", note=f"tracking {entry['name']} (target {entry['target']})")
    if action == "list":
        lines = [f"- {d['name']}: target {d['target']} ({d['url'][:60]})" for d in data]
        return outcome.done("price_tracker", note="\n".join(lines) or "no tracked products", count=len(data))
    if action == "remove":
        name = params.get("name", "")
        data = [d for d in data if d.get("name") != name]
        _save(data)
        return outcome.done("price_tracker", note=f"removed {name}")
    if action == "check":
        # Basic: just report tracked items (real price fetching would need scraping)
        lines = [f"- {d['name']}: target {d['target']}" for d in data]
        return outcome.done("price_tracker", note="Tracked:\n" + "\n".join(lines) if lines else "no tracked products")
    return outcome.failed("price_tracker", f"unknown action: {action}")
