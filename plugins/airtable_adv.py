"""JARVIS plugin - Airtable advanced (views, attachments, linked records)."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "airtable_adv",
    "description": "Airtable advanced: views, attachments, linked records.",
    "brief": "Airtable advanced: views/attachments/links.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "views|attachments|links"},
            "base_id": {"type": "STRING", "description": "Base id."},
            "table": {"type": "STRING", "description": "Table name."},
            "record_id": {"type": "STRING", "description": "Record id."},
        },
        "required": ["action", "base_id", "table"],
    },
    "tier": "extra",
}


def _token():
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        return cfg.get("airtable_token", "")
    except Exception:
        return ""


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    token = _token()
    if not token:
        return outcome.failed("airtable_adv", "Airtable token not configured")
    base_id = params.get("base_id", "")
    table = params.get("table", "")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        if action == "views":
            url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            tables = data.get("tables", [])
            lines = []
            for t in tables:
                if t["name"] == table:
                    for v in t.get("views", []):
                        lines.append(f"- {v['name']} ({v['type']})")
            return outcome.done("airtable_adv", note="\n".join(lines) or "no views", count=len(lines))
        return outcome.failed("airtable_adv", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("airtable_adv", str(e))
