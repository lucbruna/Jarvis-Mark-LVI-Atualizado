"""JARVIS plugin - HubSpot advanced (workflows, forms, emails)."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "hubspot_adv",
    "description": "HubSpot advanced: workflows, forms, email campaigns.",
    "brief": "HubSpot advanced: workflows/forms/emails.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "workflows|forms|emails"},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _token():
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        return cfg.get("hubspot_token", "")
    except Exception:
        return ""


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    token = _token()
    if not token:
        return outcome.failed("hubspot_adv", "HubSpot token not configured")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        if action == "workflows":
            req = urllib.request.Request("https://api.hubapi.com/automation/v3/workflows", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            workflows = data.get("workflows", [])
            lines = [f"- {w.get('name')} ({w.get('id')})" for w in workflows[:20]]
            return outcome.done("hubspot_adv", note="\n".join(lines) or "no workflows", count=len(workflows))
        if action == "forms":
            req = urllib.request.Request("https://api.hubapi.com/forms/v2/forms", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            forms = data if isinstance(data, list) else data.get("results", [])
            lines = [f"- {f.get('name')} ({f.get('guid')})" for f in forms[:20]]
            return outcome.done("hubspot_adv", note="\n".join(lines) or "no forms", count=len(forms))
        if action == "emails":
            req = urllib.request.Request("https://api.hubapi.com/marketing-emails/v1/emails", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            emails = data.get("objects", [])
            lines = [f"- {e.get('name')} ({e.get('state')})" for e in emails[:20]]
            return outcome.done("hubspot_adv", note="\n".join(lines) or "no emails", count=len(emails))
        return outcome.failed("hubspot_adv", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("hubspot_adv", str(e))
