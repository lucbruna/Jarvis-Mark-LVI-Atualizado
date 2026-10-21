"""JARVIS plugin - Microsoft Teams integration via webhook."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "teams",
    "description": "Send messages to Microsoft Teams via incoming webhook.",
    "brief": "Teams: send messages via webhook.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "text": {"type": "STRING", "description": "Message text."},
            "webhook_url": {"type": "STRING", "description": "Teams webhook URL (optional, uses config)."},
        },
        "required": ["text"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    text = params.get("text", "")
    webhook = params.get("webhook_url", "")
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        webhook = webhook or cfg.get("teams_webhook", "")
    except Exception:
        pass
    if not webhook:
        return outcome.failed("teams", "Teams webhook not configured")
    try:
        data = {"text": text}
        req = urllib.request.Request(webhook, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=15)
        msg = "Message sent to Teams"
        if player:
            try: player.write_log(f"JARVIS: {msg}")
            except Exception: pass
        return outcome.done("teams", note=msg)
    except Exception as e:
        return outcome.failed("teams", str(e))
