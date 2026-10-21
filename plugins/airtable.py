"""JARVIS plugin - Airtable integration."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "airtable",
    "description": "Airtable: list records, create, update.",
    "brief": "Airtable: list/create/update records.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "list|create|update"},
            "base_id": {"type": "STRING", "description": "Airtable base id."},
            "table": {"type": "STRING", "description": "Table name."},
            "record_id": {"type": "STRING", "description": "Record id (update)."},
            "fields": {"type": "STRING", "description": "JSON fields (create/update)."},
            "max_records": {"type": "INTEGER", "description": "Max records (list, default 20)."},
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
        return outcome.failed("airtable", "Airtable token not configured")
    base_id = params.get("base_id", "")
    table = params.get("table", "")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    base_url = f"https://api.airtable.com/v0/{base_id}/{table}"
    try:
        if action == "list":
            maxr = int(params.get("max_records", 20))
            req = urllib.request.Request(f"{base_url}?maxRecords={maxr}", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            records = data.get("records", [])
            lines = [f"- {r['id']}: {r.get('fields', {})}" for r in records[:20]]
            return outcome.done("airtable", note="\n".join(lines) or "no records", count=len(records))
        if action == "create":
            fields = json.loads(params.get("fields", "{}"))
            body = {"fields": fields}
            req = urllib.request.Request(base_url, data=json.dumps(body).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("airtable", note=f"created: {data.get('id')}")
        if action == "update":
            rid = params.get("record_id", "")
            fields = json.loads(params.get("fields", "{}"))
            body = {"fields": fields}
            req = urllib.request.Request(f"{base_url}/{rid}", data=json.dumps(body).encode(), headers=headers, method="PATCH")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("airtable", note=f"updated: {data.get('id')}")
        return outcome.failed("airtable", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("airtable", str(e))
