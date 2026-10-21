"""JARVIS plugin - Google Drive advanced (permissions, revisions, webhooks)."""
from __future__ import annotations

import json
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "gdrive_adv2",
    "description": "Google Drive advanced: permissions, revisions, webhooks.",
    "brief": "Google Drive advanced: permissions/revisions/webhooks.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "permissions|revisions|webhooks"},
            "file_id": {"type": "STRING", "description": "File id."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _service():
    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
    except ImportError:
        return None, "google-api-python-client not installed"
    token_path = Path.home() / ".jarvis" / "drive_token.json"
    if not token_path.exists():
        return None, "Drive not authorized"
    try:
        creds = Credentials.from_authorized_user_file(str(token_path))
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path.write_text(creds.to_json())
        return build("drive", "v3", credentials=creds), None
    except Exception as e:
        return None, str(e)


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    svc, err = _service()
    if err:
        return outcome.failed("gdrive_adv2", err)
    fid = params.get("file_id", "")
    try:
        if action == "permissions":
            res = svc.permissions().list(fileId=fid).execute()
            perms = res.get("permissions", [])
            lines = [f"- {p.get('id')}: {p.get('role')} ({p.get('type')})" for p in perms]
            return outcome.done("gdrive_adv2", note="\n".join(lines) or "no permissions", count=len(perms))
        if action == "revisions":
            res = svc.revisions().list(fileId=fid).execute()
            revs = res.get("revisions", [])
            lines = [f"- {r.get('id')}: {r.get('modifiedTime')}" for r in revs[:10]]
            return outcome.done("gdrive_adv2", note="\n".join(lines) or "no revisions", count=len(revs))
        return outcome.failed("gdrive_adv2", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("gdrive_adv2", str(e))
