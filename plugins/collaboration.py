"""JARVIS plugin - real-time collaboration via WebRTC (stub)."""
from __future__ import annotations

from core import outcome


PLUGIN = {
    "name": "collaboration",
    "description": "Real-time collaboration: share screen/session with another user via WebRTC. (Requires additional setup.)",
    "brief": "Real-time collaboration (WebRTC).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "start|stop|status"},
            "room": {"type": "STRING", "description": "Room name."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    if action == "status":
        return outcome.done("collaboration", note="WebRTC collaboration not yet implemented. Requires aiortc + signaling server.")
    return outcome.failed("collaboration", "WebRTC collaboration not implemented yet. See docs/COLLABORATION.md")
