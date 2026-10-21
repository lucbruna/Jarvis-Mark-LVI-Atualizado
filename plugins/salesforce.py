"""JARVIS plugin - Salesforce integration."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "salesforce",
    "description": "Salesforce: query SOQL, create records, list objects.",
    "brief": "Salesforce: SOQL query, create records.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "query|create|list_objects"},
            "soql": {"type": "STRING", "description": "SOQL query (query)."},
            "object": {"type": "STRING", "description": "Object name (create)."},
            "fields": {"type": "STRING", "description": "JSON fields (create)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _token():
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        # Use username-password flow or session token
        return cfg.get("salesforce_access_token", ""), cfg.get("salesforce_instance_url", "")
    except Exception:
        return "", ""


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    token, instance = _token()
    if not token or not instance:
        return outcome.failed("salesforce", "Salesforce not configured (access_token/instance_url)")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        if action == "query":
            soql = params.get("soql", "SELECT Id, Name FROM Account LIMIT 10")
            import urllib.parse
            url = f"{instance}/services/data/v58.0/query?q={urllib.parse.quote(soql)}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            records = data.get("records", [])
            lines = [str(r) for r in records[:10]]
            return outcome.done("salesforce", note="\n".join(lines) or "no records", count=len(records))
        if action == "create":
            obj = params.get("object", "Account")
            fields = json.loads(params.get("fields", "{}"))
            url = f"{instance}/services/data/v58.0/sobjects/{obj}"
            req = urllib.request.Request(url, data=json.dumps(fields).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("salesforce", note=f"created: {data.get('id')}")
        if action == "list_objects":
            url = f"{instance}/services/data/v58.0/sobjects"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            objs = [o["name"] for o in data.get("sobjects", [])[:30]]
            return outcome.done("salesforce", note="\n".join(objs), count=len(objs))
        return outcome.failed("salesforce", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("salesforce", str(e))
