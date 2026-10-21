"""JARVIS plugin - SharePoint integration via Microsoft Graph."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "sharepoint",
    "description": "SharePoint: list sites, lists, items; create list items.",
    "brief": "SharePoint: sites/lists/items.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "sites|lists|items|create_item"},
            "site_id": {"type": "STRING", "description": "Site id."},
            "list_id": {"type": "STRING", "description": "List id."},
            "fields": {"type": "STRING", "description": "JSON fields (create_item)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _token():
    try:
        import msal
    except ImportError:
        return None, "msal not installed"
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        app = msal.PublicClientApplication(cfg.get("sharepoint_client_id", ""), authority="https://login.microsoftonline.com/common")
        accounts = app.get_accounts()
        if not accounts:
            return None, "SharePoint not authorized"
        result = app.acquire_token_silent(["Sites.Read.All", "Sites.ReadWrite.All"], account=accounts[0])
        if not result or "access_token" not in result:
            return None, "Token acquisition failed"
        return result["access_token"], None
    except Exception as e:
        return None, str(e)


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    token, err = _token()
    if err:
        return outcome.failed("sharepoint", err)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        if action == "sites":
            req = urllib.request.Request("https://graph.microsoft.com/v1.0/sites?search=", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            sites = data.get("value", [])
            lines = [f"- {s.get('displayName', '?')} ({s.get('id')})" for s in sites]
            return outcome.done("sharepoint", note="\n".join(lines) or "no sites", count=len(sites))
        if action == "lists":
            sid = params.get("site_id", "")
            req = urllib.request.Request(f"https://graph.microsoft.com/v1.0/sites/{sid}/lists", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            lists = data.get("value", [])
            lines = [f"- {l.get('displayName', '?')} ({l.get('id')})" for l in lists]
            return outcome.done("sharepoint", note="\n".join(lines) or "no lists", count=len(lists))
        if action == "items":
            sid = params.get("site_id", "")
            lid = params.get("list_id", "")
            req = urllib.request.Request(f"https://graph.microsoft.com/v1.0/sites/{sid}/lists/{lid}/items?expand=fields", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            items = data.get("value", [])
            lines = [f"- {i.get('id')}: {i.get('fields', {})}" for i in items[:20]]
            return outcome.done("sharepoint", note="\n".join(lines) or "no items", count=len(items))
        if action == "create_item":
            sid = params.get("site_id", "")
            lid = params.get("list_id", "")
            fields = json.loads(params.get("fields", "{}"))
            body = {"fields": fields}
            req = urllib.request.Request(f"https://graph.microsoft.com/v1.0/sites/{sid}/lists/{lid}/items", data=json.dumps(body).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("sharepoint", note=f"created item: {data.get('id')}")
        return outcome.failed("sharepoint", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("sharepoint", str(e))
