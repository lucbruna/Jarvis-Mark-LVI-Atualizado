"""JARVIS plugin - Box advanced (metadata, collaborations, webhooks)."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "box_adv",
    "description": "Box advanced: metadata, collaborations, webhooks.",
    "brief": "Box advanced: metadata/collabs/webhooks.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "metadata|collaborations|webhooks"},
            "file_id": {"type": "STRING", "description": "File id."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _token():
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        return cfg.get("box_access_token", "")
    except Exception:
        return ""


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    token = _token()
    if not token:
        return outcome.failed("box_adv", "Box access token not configured")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        if action == "metadata":
            fid = params.get("file_id", "")
            req = urllib.request.Request(f"https://api.box.com/2.0/files/{fid}/metadata", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("box_adv", note=json.dumps(data, indent=2)[:500])
        if action == "collaborations":
            fid = params.get("file_id", "")
            req = urllib.request.Request(f"https://api.box.com/2.0/files/{fid}/collaborations", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            collabs = data.get("entries", [])
            lines = [f"- {c.get('accessible_by', {}).get('name')} ({c.get('role')})" for c in collabs]
            return outcome.done("box_adv", note="\n".join(lines) or "no collaborations", count=len(collabs))
        if action == "webhooks":
            req = urllib.request.Request("https://api.box.com/2.0/webhooks", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            hooks = data.get("entries", [])
            lines = [f"- {h.get('id')}: {h.get('trigger')}" for h in hooks]
            return outcome.done("box_adv", note="\n".join(lines) or "no webhooks", count=len(hooks))
        return outcome.failed("box_adv", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("box_adv", str(e))
