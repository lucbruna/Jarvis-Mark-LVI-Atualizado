"""JARVIS plugin - Confluence integration."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "confluence",
    "description": "Confluence: search pages, create pages, get page content.",
    "brief": "Confluence: search/create/get pages.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "search|create|get"},
            "query": {"type": "STRING", "description": "Search query (search)."},
            "space": {"type": "STRING", "description": "Space key (create)."},
            "title": {"type": "STRING", "description": "Page title (create)."},
            "content": {"type": "STRING", "description": "Page content (create)."},
            "page_id": {"type": "STRING", "description": "Page id (get)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _cfg():
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        return cfg.get("confluence_url", ""), cfg.get("confluence_email", ""), cfg.get("confluence_token", "")
    except Exception:
        return "", "", ""


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    url, email, token = _cfg()
    if not url or not token:
        return outcome.failed("confluence", "Confluence not configured")
    import base64
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
    base = url.rstrip("/")
    try:
        if action == "search":
            q = params.get("query", "")
            req = urllib.request.Request(f"{base}/rest/api/content/search?cql=text~\"{q}\"&limit=10", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            results = data.get("results", [])
            lines = [f"- {r.get('title')} ({r.get('id')})" for r in results]
            return outcome.done("confluence", note="\n".join(lines) or "no results", count=len(results))
        if action == "create":
            body = {"type": "page", "title": params.get("title", ""), "space": {"key": params.get("space", "")},
                    "body": {"storage": {"value": params.get("content", ""), "representation": "storage"}}}
            req = urllib.request.Request(f"{base}/rest/api/content", data=json.dumps(body).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("confluence", note=f"created page: {data.get('id')}")
        if action == "get":
            pid = params.get("page_id", "")
            req = urllib.request.Request(f"{base}/rest/api/content/{pid}?expand=body.storage", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            body = data.get("body", {}).get("storage", {}).get("value", "")
            # strip tags
            import re
            text = re.sub(r"<[^>]+>", " ", body)
            text = " ".join(text.split())[:2000]
            return outcome.done("confluence", note=f"{data.get('title')}\n{text}", title=data.get("title"), content=text)
        return outcome.failed("confluence", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("confluence", str(e))
