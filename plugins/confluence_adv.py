"""JARVIS plugin - Confluence advanced (update, delete, attachments)."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "confluence_adv",
    "description": "Confluence advanced: update page, delete page, add comment, list spaces.",
    "brief": "Confluence advanced: update/delete/comment/spaces.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "update|delete|comment|spaces"},
            "page_id": {"type": "STRING", "description": "Page id (update/delete/comment)."},
            "title": {"type": "STRING", "description": "New title (update)."},
            "content": {"type": "STRING", "description": "New content (update/comment)."},
            "version": {"type": "INTEGER", "description": "Current version number (update)."},
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
        return outcome.failed("confluence_adv", "Confluence not configured")
    import base64
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
    base = url.rstrip("/")
    try:
        if action == "spaces":
            req = urllib.request.Request(f"{base}/rest/api/space?limit=20", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            spaces = data.get("results", [])
            lines = [f"- {s.get('key')}: {s.get('name')}" for s in spaces]
            return outcome.done("confluence_adv", note="\n".join(lines) or "no spaces", count=len(spaces))
        if action == "update":
            pid = params.get("page_id", "")
            version = int(params.get("version", 1))
            body = {"id": pid, "type": "page", "title": params.get("title", ""), "body": {"storage": {"value": params.get("content", ""), "representation": "storage"}}, "version": {"number": version + 1}}
            req = urllib.request.Request(f"{base}/rest/api/content/{pid}", data=json.dumps(body).encode(), headers=headers, method="PUT")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("confluence_adv", note=f"updated page: {data.get('id')}")
        if action == "delete":
            pid = params.get("page_id", "")
            req = urllib.request.Request(f"{base}/rest/api/content/{pid}", headers=headers, method="DELETE")
            with urllib.request.urlopen(req, timeout=15) as r:
                pass
            return outcome.done("confluence_adv", note=f"deleted page: {pid}")
        if action == "comment":
            pid = params.get("page_id", "")
            body = {"type": "comment", "container": {"id": pid, "type": "page"}, "body": {"storage": {"value": params.get("content", ""), "representation": "storage"}}}
            req = urllib.request.Request(f"{base}/rest/api/content", data=json.dumps(body).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("confluence_adv", note=f"comment added: {data.get('id')}")
        return outcome.failed("confluence_adv", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("confluence_adv", str(e))
