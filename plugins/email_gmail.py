"""JARVIS plugin - email via Gmail API (OAuth)."""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "email_gmail",
    "description": "Send, search, and read emails via Gmail. Requires Gmail API credentials (OAuth). Actions: send, search, read, list.",
    "brief": "Gmail: send/search/read emails.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "send|search|read|list"},
            "to": {"type": "STRING", "description": "Recipient email (send)."},
            "subject": {"type": "STRING", "description": "Email subject (send)."},
            "body": {"type": "STRING", "description": "Email body (send)."},
            "query": {"type": "STRING", "description": "Search query (search)."},
            "message_id": {"type": "STRING", "description": "Message id (read)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _creds_path():
    return Path.home() / ".jarvis" / "gmail_credentials.json"


def _get_service():
    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
    except ImportError:
        return None, "google-api-python-client not installed. Run: pip install google-api-python-client google-auth-oauthlib"
    token_path = Path.home() / ".jarvis" / "gmail_token.json"
    if not token_path.exists():
        return None, "Gmail not authorized. Run OAuth flow first."
    try:
        creds = Credentials.from_authorized_user_file(str(token_path))
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path.write_text(creds.to_json())
        return build("gmail", "v1", credentials=creds), None
    except Exception as e:
        return None, f"Gmail auth failed: {e}"


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    svc, err = _get_service()
    if err:
        return outcome.failed("email_gmail", err)

    try:
        if action == "send":
            from email.mime.text import MIMEText
            import base64
            msg = MIMEText(params.get("body", ""))
            msg["to"] = params.get("to", "")
            msg["subject"] = params.get("subject", "")
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            svc.users().messages().send(userId="me", body={"raw": raw}).execute()
            msg_out = f"Email sent to {params.get('to')}"
            if player:
                try: player.write_log(f"JARVIS: {msg_out}")
                except Exception: pass
            return outcome.done("email_gmail", note=msg_out)

        if action == "search":
            q = params.get("query", "")
            res = svc.users().messages().list(userId="me", q=q, maxResults=10).execute()
            msgs = res.get("messages", [])
            lines = []
            for m in msgs:
                d = svc.users().messages().get(userId="me", id=m["id"], format="metadata", metadataHeaders=["Subject", "From"]).execute()
                headers = {h["name"]: h["value"] for h in d.get("payload", {}).get("headers", [])}
                lines.append(f"- {headers.get('Subject','(no subject)')} — from {headers.get('From','?')}")
            out = f"Found {len(msgs)} emails:\n" + "\n".join(lines) if lines else "No emails found."
            return outcome.done("email_gmail", note=out[:500], count=len(msgs))

        if action == "read":
            mid = params.get("message_id", "")
            if not mid:
                return outcome.failed("email_gmail", "message_id required")
            d = svc.users().messages().get(userId="me", id=mid, format="full").execute()
            body = ""
            payload = d.get("payload", {})
            parts = payload.get("parts", [payload])
            for part in parts:
                if part.get("mimeType") == "text/plain":
                    import base64
                    data = part.get("body", {}).get("data", "")
                    body = base64.urlsafe_b64decode(data).decode("utf-8", "replace")
                    break
            subject = next((h["value"] for h in payload.get("headers", []) if h["name"] == "Subject"), "")
            return outcome.done("email_gmail", note=f"Subject: {subject}\n{body[:1000]}", subject=subject, body=body)

        if action == "list":
            res = svc.users().messages().list(userId="me", maxResults=10).execute()
            msgs = res.get("messages", [])
            return outcome.done("email_gmail", note=f"{len(msgs)} recent emails", count=len(msgs))

        return outcome.failed("email_gmail", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("email_gmail", str(e))
