"""JARVIS plugin - Google Sheets integration."""
from __future__ import annotations

import json
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "google_sheets",
    "description": "Read/write Google Sheets. Actions: read, append, update.",
    "brief": "Google Sheets: read/append/update.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "read|append|update"},
            "spreadsheet_id": {"type": "STRING", "description": "Spreadsheet ID."},
            "range": {"type": "STRING", "description": "Range (e.g. Sheet1!A1:D10)."},
            "values": {"type": "STRING", "description": "JSON values (append/update)."},
        },
        "required": ["action", "spreadsheet_id"],
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
    token_path = Path.home() / ".jarvis" / "sheets_token.json"
    if not token_path.exists():
        return None, "Sheets not authorized. Run OAuth flow first."
    try:
        creds = Credentials.from_authorized_user_file(str(token_path))
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path.write_text(creds.to_json())
        return build("sheets", "v4", credentials=creds), None
    except Exception as e:
        return None, str(e)


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    sid = params.get("spreadsheet_id", "")
    rng = params.get("range", "Sheet1!A1:Z100")
    svc, err = _service()
    if err:
        return outcome.failed("google_sheets", err)
    try:
        if action == "read":
            res = svc.spreadsheets().values().get(spreadsheetId=sid, range=rng).execute()
            values = res.get("values", [])
            lines = [" | ".join(row) for row in values[:30]]
            return outcome.done("google_sheets", note="\n".join(lines) or "empty", rows=values)
        if action in ("append", "update"):
            values = json.loads(params.get("values", "[]"))
            body = {"values": values if isinstance(values, list) else [values]}
            if action == "append":
                res = svc.spreadsheets().values().append(spreadsheetId=sid, range=rng, valueInputOption="USER_ENTERED", body=body).execute()
            else:
                res = svc.spreadsheets().values().update(spreadsheetId=sid, range=rng, valueInputOption="USER_ENTERED", body=body).execute()
            return outcome.done("google_sheets", note=f"{action}: {res.get('updatedCells', 0)} cells")
        return outcome.failed("google_sheets", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("google_sheets", str(e))
