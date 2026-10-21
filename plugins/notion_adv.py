"""JARVIS plugin - Notion advanced (databases, relations, rollups)."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "notion_adv",
    "description": "Notion advanced: query databases with filters, create pages with relations.",
    "brief": "Notion advanced: db query/relations.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "query_db|create_page"},
            "database_id": {"type": "STRING", "description": "Database id."},
            "filter": {"type": "STRING", "description": "Filter property (query_db)."},
            "value": {"type": "STRING", "description": "Filter value (query_db)."},
            "properties": {"type": "STRING", "description": "JSON properties (create_page)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _token():
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        return cfg.get("notion_token", "")
    except Exception:
        return ""


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    token = _token()
    if not token:
        return outcome.failed("notion_adv", "Notion token not configured")
    headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
    try:
        if action == "query_db":
            db_id = params.get("database_id", "")
            body = {}
            if params.get("filter") and params.get("value"):
                body["filter"] = {"property": params["filter"], "rich_text": {"equals": params["value"]}}
            req = urllib.request.Request(f"https://api.notion.com/v1/databases/{db_id}/query", data=json.dumps(body).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            results = data.get("results", [])
            lines = [f"- {r['id']}" for r in results[:10]]
            return outcome.done("notion_adv", note="\n".join(lines) or "no results", count=len(results))
        if action == "create_page":
            db_id = params.get("database_id", "")
            props = json.loads(params.get("properties", "{}"))
            body = {"parent": {"database_id": db_id}, "properties": props}
            req = urllib.request.Request("https://api.notion.com/v1/pages", data=json.dumps(body).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("notion_adv", note=f"created page: {data.get('id')}")
        return outcome.failed("notion_adv", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("notion_adv", str(e))
