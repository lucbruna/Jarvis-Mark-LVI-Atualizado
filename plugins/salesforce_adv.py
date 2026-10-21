"""JARVIS plugin - Salesforce advanced (SOQL, bulk, apex)."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "salesforce_adv",
    "description": "Salesforce advanced: SOQL query, bulk operations, describe objects.",
    "brief": "Salesforce advanced: SOQL/bulk/describe.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "query|describe|list_objects"},
            "soql": {"type": "STRING", "description": "SOQL query (query)."},
            "object": {"type": "STRING", "description": "Object name (describe)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _cfg():
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        return cfg.get("salesforce_access_token", ""), cfg.get("salesforce_instance_url", "")
    except Exception:
        return "", ""


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    token, instance = _cfg()
    if not token or not instance:
        return outcome.failed("salesforce_adv", "Salesforce not configured")
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
            return outcome.done("salesforce_adv", note="\n".join(lines) or "no records", count=len(records))
        if action == "describe":
            obj = params.get("object", "Account")
            url = f"{instance}/services/data/v58.0/sobjects/{obj}/describe"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            fields = [f"{f['name']}: {f['type']}" for f in data.get("fields", [])[:20]]
            return outcome.done("salesforce_adv", note="\n".join(fields), count=len(fields))
        if action == "list_objects":
            url = f"{instance}/services/data/v58.0/sobjects"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            objs = [o["name"] for o in data.get("sobjects", [])]
            return outcome.done("salesforce_adv", note="\n".join(objs[:30]), count=len(objs))
        return outcome.failed("salesforce_adv", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("salesforce_adv", str(e))
