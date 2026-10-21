"""JARVIS plugin - Notion database query."""
from __future__ import annotations

import json
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "notion_db",
    "description": "Query Notion databases: list pages, filter, create entries.",
    "brief": "Notion database: query/create.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "query|create"},
            "database_id": {"type": "STRING", "description": "Notion database id."},
            "filter": {"type": "STRING", "description": "Filter property name (query)."},
            "value": {"type": "STRING", "description": "Filter value (query)."},
            "properties": {"type": "STRING", "description": "JSON properties (create)."},
        },
        "required": ["action", "database_id"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    db_id = params.get("database_id", "")
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        token = cfg.get("notion_token", "")
    except Exception:
        token = ""
    if not token:
        return outcome.failed("notion_db", "Notion token not configured")
    import urllib.request
    headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
    try:
        if action == "query":
            body = {}
            if params.get("filter") and params.get("value"):
                body["filter"] = {"property": params["filter"], "rich_text": {"equals": params["value"]}}
            req = urllib.request.Request(f"https://api.notion.com/v1/databases/{db_id}/query", data=__import__("json").dumps(body).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            results = data.get("results", [])
            lines = []
            for r in results[:10]:
                props = r.get("properties", {})
                title = ""
                for k, v in props.items():
                    if v.get("type") == "title" and v.get("title"):
                        title = v["title"][0].get("text", {}).get("content", "")
                lines.append(f"- {title or r['id']}")
            return outcome.done("notion_db", note="\n".join(lines) or "no results", count=len(results))
        if action == "create":
            props = json.loads(params.get("properties", "{}"))
            body = {"parent": {"database_id": db_id}, "properties": props}
            req = urllib.request.Request("https://api.notion.com/v1/pages", data=json.dumps(body).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("notion_db", note=f"created page: {data.get('id')}")
        return outcome.failed("notion_db", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("notion_db", str(e))
