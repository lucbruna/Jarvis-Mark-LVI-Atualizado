"""JARVIS plugin - SharePoint advanced (sites, permissions, webhooks)."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "sharepoint_adv",
    "description": "SharePoint advanced: sites, permissions, webhooks.",
    "brief": "SharePoint advanced: sites/permissions/webhooks.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "sites|permissions|webhooks"},
            "site_id": {"type": "STRING", "description": "Site id (permissions)."},
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
        return outcome.failed("sharepoint_adv", err)
    headers = {"Authorization": f"Bearer {token}"}
    try:
        if action == "sites":
            req = urllib.request.Request("https://graph.microsoft.com/v1.0/sites?search=", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            sites = data.get("value", [])
            lines = [f"- {s.get('displayName', '?')} ({s.get('id')})" for s in sites]
            return outcome.done("sharepoint_adv", note="\n".join(lines) or "no sites", count=len(sites))
        if action == "permissions":
            sid = params.get("site_id", "")
            req = urllib.request.Request(f"https://graph.microsoft.com/v1.0/sites/{sid}/permissions", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            perms = data.get("value", [])
            lines = [f"- {p.get('id')}: {p.get('roles')}" for p in perms]
            return outcome.done("sharepoint_adv", note="\n".join(lines) or "no permissions", count=len(perms))
        if action == "webhooks":
            sid = params.get("site_id", "")
            req = urllib.request.Request(f"https://graph.microsoft.com/v1.0/sites/{sid}/subscriptions", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            subs = data.get("value", [])
            lines = [f"- {s.get('id')}: {s.get('resource')}" for s in subs]
            return outcome.done("sharepoint_adv", note="\n".join(lines) or "no webhooks", count=len(subs))
        return outcome.failed("sharepoint_adv", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("sharepoint_adv", str(e))
