"""JARVIS plugin - Google Meet integration (create meeting links)."""
from __future__ import annotations

import json
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "google_meet",
    "description": "Create Google Meet links via Google Calendar API.",
    "brief": "Google Meet: create meeting links.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "create (default)"},
            "title": {"type": "STRING", "description": "Meeting title."},
            "start": {"type": "STRING", "description": "Start datetime ISO."},
            "end": {"type": "STRING", "description": "End datetime ISO."},
            "attendees": {"type": "STRING", "description": "Comma-separated emails."},
        },
        "required": [],
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
    token_path = Path.home() / ".jarvis" / "calendar_token.json"
    if not token_path.exists():
        return None, "Google Calendar not authorized. Run OAuth flow first."
    try:
        creds = Credentials.from_authorized_user_file(str(token_path))
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path.write_text(creds.to_json())
        return build("calendar", "v3", credentials=creds), None
    except Exception as e:
        return None, str(e)


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "create").lower()
    if action != "create":
        return outcome.failed("google_meet", f"unknown action: {action}")
    svc, err = _service()
    if err:
        return outcome.failed("google_meet", err)
    try:
        event = {
            "summary": params.get("title", "JARVIS Meeting"),
            "start": {"dateTime": params.get("start"), "timeZone": "UTC"},
            "end": {"dateTime": params.get("end"), "timeZone": "UTC"},
            "conferenceData": {"createRequest": {"requestId": f"meet-{int(__import__('time').time())}", "conferenceSolutionKey": {"type": "hangoutsMeet"}}},
        }
        if params.get("attendees"):
            event["attendees"] = [{"email": e.strip()} for e in params["attendees"].split(",")]
        created = svc.events().insert(calendarId="primary", body=event, conferenceDataVersion=1).execute()
        meet_link = created.get("hangoutLink", "")
        msg = f"Meet link: {meet_link}"
        if player:
            try: player.write_log(f"JARVIS: {msg}")
            except Exception: pass
        return outcome.done("google_meet", note=msg, link=meet_link)
    except Exception as e:
        return outcome.failed("google_meet", str(e))
