"""JARVIS plugin - Webex integration."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "webex",
    "description": "Send messages to Webex via bot token.",
    "brief": "Webex: send messages.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "send (default)"},
            "text": {"type": "STRING", "description": "Message text."},
            "room_id": {"type": "STRING", "description": "Room ID (optional, uses config)."},
        },
        "required": ["text"],
    },
    "tier": "extra",
}


def _token():
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        return cfg.get("webex_token", "")
    except Exception:
        return ""


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    token = _token()
    if not token:
        return outcome.failed("webex", "Webex token not configured")
    room_id = params.get("room_id", "")
    if not room_id:
        try:
            cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
            room_id = cfg.get("webex_room_id", "")
        except Exception:
            pass
    if not room_id:
        return outcome.failed("webex", "room_id required")
    try:
        data = {"roomId": room_id, "text": params.get("text", "")}
        req = urllib.request.Request("https://webexapis.com/v1/messages", data=json.dumps(data).encode(), headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as r:
            res = json.loads(r.read())
        msg = f"Webex message sent: {res.get('id')}"
        if player:
            try: player.write_log(f"JARVIS: {msg}")
            except Exception: pass
        return outcome.done("webex", note=msg)
    except Exception as e:
        return outcome.failed("webex", str(e))
