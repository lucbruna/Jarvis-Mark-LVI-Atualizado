"""JARVIS plugin - OneDrive advanced (permissions, versions, webhooks)."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "onedrive_adv2",
    "description": "OneDrive advanced: permissions, versions, webhooks.",
    "brief": "OneDrive advanced: permissions/versions/webhooks.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "permissions|versions|webhooks"},
            "item_id": {"type": "STRING", "description": "Item id."},
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
        app = msal.PublicClientApplication(cfg.get("onedrive_client_id", ""), authority="https://login.microsoftonline.com/common")
        accounts = app.get_accounts()
        if not accounts:
            return None, "OneDrive not authorized"
        result = app.acquire_token_silent(["Files.ReadWrite.All"], account=accounts[0])
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
        return outcome.failed("onedrive_adv2", err)
    headers = {"Authorization": f"Bearer {token}"}
    iid = params.get("item_id", "")
    try:
        if action == "permissions":
            req = urllib.request.Request(f"https://graph.microsoft.com/v1.0/me/drive/items/{iid}/permissions", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            perms = data.get("value", [])
            lines = [f"- {p.get('id')}: {p.get('roles')}" for p in perms]
            return outcome.done("onedrive_adv2", note="\n".join(lines) or "no permissions", count=len(perms))
        if action == "versions":
            req = urllib.request.Request(f"https://graph.microsoft.com/v1.0/me/drive/items/{iid}/versions", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            versions = data.get("value", [])
            lines = [f"- {v.get('id')}: {v.get('lastModifiedDateTime')}" for v in versions]
            return outcome.done("onedrive_adv2", note="\n".join(lines) or "no versions", count=len(versions))
        if action == "webhooks":
            req = urllib.request.Request("https://graph.microsoft.com/v1.0/subscriptions", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            subs = data.get("value", [])
            lines = [f"- {s.get('id')}: {s.get('resource')}" for s in subs]
            return outcome.done("onedrive_adv2", note="\n".join(lines) or "no webhooks", count=len(subs))
        return outcome.failed("onedrive_adv2", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("onedrive_adv2", str(e))
