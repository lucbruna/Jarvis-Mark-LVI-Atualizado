"""JARVIS plugin - Outlook/Exchange email via Microsoft Graph."""
from __future__ import annotations

import json
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "email_outlook",
    "description": "Send/read/search emails via Microsoft Graph (Outlook/Exchange). Requires Azure app credentials.",
    "brief": "Outlook/Exchange email via Microsoft Graph.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "send|search|read|list"},
            "to": {"type": "STRING", "description": "Recipient (send)."},
            "subject": {"type": "STRING", "description": "Subject (send)."},
            "body": {"type": "STRING", "description": "Body (send)."},
            "query": {"type": "STRING", "description": "Search query (search)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _token():
    try:
        import msal
    except ImportError:
        return None, "msal not installed. Run: pip install msal"
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        app = msal.PublicClientApplication(cfg.get("outlook_client_id", ""), authority="https://login.microsoftonline.com/consumers")
        accounts = app.get_accounts()
        if not accounts:
            return None, "Outlook not authorized. Run OAuth flow first."
        result = app.acquire_token_silent(["Mail.Read", "Mail.Send"], account=accounts[0])
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
        return outcome.failed("email_outlook", err)
    import urllib.request
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        if action == "send":
            data = {"message": {"subject": params.get("subject", ""), "body": {"contentType": "Text", "content": params.get("body", "")},
                    "toRecipients": [{"emailAddress": {"address": params.get("to", "")}}]}, "saveToSentItems": True}
            req = urllib.request.Request("https://graph.microsoft.com/v1.0/me/sendMail", data=__import__("json").dumps(data).encode(), headers=headers, method="POST")
            urllib.request.urlopen(req, timeout=30)
            return outcome.done("email_outlook", note=f"Email sent to {params.get('to')}")
        if action == "list":
            req = urllib.request.Request("https://graph.microsoft.com/v1.0/me/messages?$top=10&$select=subject,from", headers=headers)
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read())
            lines = [f"- {m.get('subject', '(no subject)')} — {m.get('from', {}).get('emailAddress', {}).get('address', '?')}" for m in data.get("value", [])]
            return outcome.done("email_outlook", note="\n".join(lines) or "no emails", count=len(data.get("value", [])))
        return outcome.failed("email_outlook", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("email_outlook", str(e))
