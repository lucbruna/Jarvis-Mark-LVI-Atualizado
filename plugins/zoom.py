"""JARVIS plugin - Zoom integration (create meetings)."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "zoom",
    "description": "Create Zoom meetings via Zoom API. Requires Server-to-Server OAuth credentials.",
    "brief": "Zoom: create meetings.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "create_meeting (default)"},
            "topic": {"type": "STRING", "description": "Meeting topic."},
            "duration": {"type": "INTEGER", "description": "Duration in minutes (default 30)."},
            "start_time": {"type": "STRING", "description": "Start time ISO (optional)."},
        },
        "required": [],
    },
    "tier": "extra",
}


def _token():
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        import base64
        creds = base64.b64encode(f"{cfg.get('zoom_client_id','')}:{cfg.get('zoom_client_secret','')}".encode()).decode()
        data = urllib.parse.urlencode({"grant_type": "account_credentials", "account_id": cfg.get("zoom_account_id", "")}).encode() if False else __import__("urllib.parse").urlencode({"grant_type": "account_credentials", "account_id": cfg.get("zoom_account_id", "")}).encode()
        req = urllib.request.Request("https://zoom.us/oauth/token", data=data, headers={"Authorization": f"Basic {creds}", "Content-Type": "application/x-www-form-urlencoded"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read()).get("access_token"), None
    except Exception as e:
        return None, str(e)


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "create_meeting").lower()
    token, err = _token()
    if err:
        return outcome.failed("zoom", err)
    if action == "create_meeting":
        body = {"topic": params.get("topic", "JARVIS Meeting"), "type": 2, "duration": int(params.get("duration", 30))}
        if params.get("start_time"):
            body["start_time"] = params["start_time"]
        req = urllib.request.Request("https://api.zoom.us/v2/users/me/meetings", data=json.dumps(body).encode(), headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            msg = f"Meeting created: {data.get('join_url')}"
            if player:
                try: player.write_log(f"JARVIS: {msg}")
                except Exception: pass
            return outcome.done("zoom", note=msg, join_url=data.get("join_url"), meeting_id=data.get("id"))
        except Exception as e:
            return outcome.failed("zoom", str(e))
    return outcome.failed("zoom", f"unknown action: {action}")
