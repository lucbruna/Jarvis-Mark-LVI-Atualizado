"""JARVIS plugin - trigger Zapier/Make webhooks."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "webhook_trigger",
    "description": "Trigger a Zapier/Make/n8n webhook with JSON payload. Use to automate external workflows.",
    "brief": "Trigger webhooks (Zapier/Make/n8n).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "url": {"type": "STRING", "description": "Webhook URL."},
            "payload": {"type": "STRING", "description": "JSON payload (string)."},
            "method": {"type": "STRING", "description": "POST (default) or GET."},
        },
        "required": ["url"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    url = params.get("url", "")
    method = (params.get("method") or "POST").upper()
    payload = params.get("payload", "{}")
    try:
        data = json.loads(payload) if payload else {}
    except Exception:
        data = {"raw": payload}
    try:
        if method == "GET":
            req = urllib.request.Request(url, method="GET")
        else:
            req = urllib.request.Request(url, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = r.read().decode("utf-8", "replace")[:500]
        msg = f"Webhook triggered: {resp or 'OK'}"
        if player:
            try: player.write_log(f"JARVIS: {msg}")
            except Exception: pass
        return outcome.done("webhook_trigger", note=msg)
    except Exception as e:
        return outcome.failed("webhook_trigger", str(e))
