"""JARVIS plugin - travel assistant: flights, hotels, weather."""
from __future__ import annotations

from core import outcome


PLUGIN = {
    "name": "travel_assistant",
    "description": "Travel planning: search flights, hotels, and weather for a destination. Uses web_search.",
    "brief": "Travel: flights, hotels, weather.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "destination": {"type": "STRING", "description": "Destination city/country."},
            "action": {"type": "STRING", "description": "flights|hotels|weather|plan (default plan)."},
            "dates": {"type": "STRING", "description": "Travel dates."},
        },
        "required": ["destination"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    dest = params.get("destination", "")
    action = (params.get("action") or "plan").lower()
    dates = params.get("dates", "")
    try:
        from actions.web_search import _search
    except Exception:
        return outcome.failed("travel_assistant", "web_search not available")
    queries = {
        "flights": f"flights to {dest} {dates}",
        "hotels": f"hotels in {dest} {dates}",
        "weather": f"weather in {dest}",
        "plan": f"travel guide {dest} {dates}",
    }
    q = queries.get(action, queries["plan"])
    try:
        res = _search(q)
    except Exception as e:
        res = f"Search failed: {e}"
    msg = f"Travel info for {dest}:\n{res[:1000]}"
    if player:
        try: player.write_log(f"JARVIS: {msg[:300]}")
        except Exception: pass
    return outcome.done("travel_assistant", note=msg[:500], destination=dest)
