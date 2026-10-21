"""JARVIS plugin - health tracking (steps, sleep, medication)."""
from __future__ import annotations

import json
import time
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "health",
    "description": "Track health metrics: steps, sleep hours, medication reminders. Actions: log, summary, list.",
    "brief": "Health: log steps/sleep/medication, summary.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "log|summary|list"},
            "metric": {"type": "STRING", "description": "steps|sleep|medication|weight"},
            "value": {"type": "NUMBER", "description": "Value (log)."},
            "note": {"type": "STRING", "description": "Note (log)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}

_STORE = Path(__file__).resolve().parents[1] / "memory" / "health.json"


def _load():
    try:
        if _STORE.exists():
            return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"entries": []}


def _save(d):
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    d = _load()
    if action == "log":
        entry = {"metric": params.get("metric", "steps"), "value": params.get("value", 0),
                 "note": params.get("note", ""), "date": time.strftime("%Y-%m-%d"), "ts": time.time()}
        d["entries"].append(entry)
        _save(d)
        return outcome.done("health", note=f"logged {entry['metric']}: {entry['value']}")
    if action == "list":
        lines = [f"- {e['date']}: {e['metric']} {e['value']} {e.get('note','')}" for e in d["entries"][-20:]]
        return outcome.done("health", note="\n".join(lines) or "no entries", count=len(d["entries"]))
    if action == "summary":
        from collections import defaultdict
        totals = defaultdict(float)
        for e in d["entries"]:
            totals[e.get("metric", "?")] += float(e.get("value", 0) or 0)
        msg = ", ".join(f"{k}: {v}" for k, v in totals.items())
        return outcome.done("health", note=msg or "no data")
    return outcome.failed("health", f"unknown action: {action}")
