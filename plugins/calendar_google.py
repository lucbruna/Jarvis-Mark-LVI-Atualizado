"""JARVIS plugin - Google Calendar integration."""
from __future__ import annotations

import threading
import time
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "calendar_google",
    "description": "Manage Google Calendar: list events, create events, delete events. Requires OAuth credentials.",
    "brief": "Google Calendar: list/create/delete events.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "list|create|delete"},
            "title": {"type": "STRING", "description": "Event title (create)."},
            "start": {"type": "STRING", "description": "Start datetime ISO (create)."},
            "end": {"type": "STRING", "description": "End datetime ISO (create)."},
            "event_id": {"type": "STRING", "description": "Event id (delete)."},
            "days": {"type": "INTEGER", "description": "Days ahead to list (default 7)."},
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
    token_path = Path.home() / ".jarvis" / "calendar_token.json"
    if not token_path.exists():
        return None, "Calendar not authorized. Run OAuth flow first."
    try:
        creds = Credentials.from_authorized_user_file(str(token_path))
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path.write_text(creds.to_json())
        return build("calendar", "v3", credentials=creds), None
    except Exception as e:
        return None, f"Calendar auth failed: {e}"


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    svc, err = _service()
    if err:
        return outcome.failed("calendar_google", err)
    try:
        if action == "list":
            from datetime import datetime, timedelta, timezone
            now = datetime.now(timezone.utc).isoformat()
            end = (datetime.now(timezone.utc) + timedelta(days=int(params.get("days", 7)))).isoformat()
            events = svc.events().list(calendarId="primary", timeMin=now, timeMax=end, singleEvents=True, orderBy="startTime").execute().get("items", [])
            lines = []
            for e in events:
                start = e["start"].get("dateTime", e["start"].get("date"))
                lines.append(f"- {start}: {e.get('summary', '(no title)')}")
            out = f"{len(events)} upcoming events:\n" + "\n".join(lines) if lines else "No upcoming events."
            return outcome.done("calendar_google", note=out[:500], count=len(events))

        if action == "create":
            event = {
                "summary": params.get("title", "New event"),
                "start": {"dateTime": params.get("start"), "timeZone": "UTC"},
                "end": {"dateTime": params.get("end"), "timeZone": "UTC"},
            }
            created = svc.events().insert(calendarId="primary", body=event).execute()
            msg = f"Event created: {created.get('htmlLink')}"
            if player:
                try: player.write_log(f"JARVIS: {msg}")
                except Exception: pass
            return outcome.done("calendar_google", note=msg, event_id=created.get("id"))

        if action == "delete":
            eid = params.get("event_id", "")
            if not eid:
                return outcome.failed("calendar_google", "event_id required")
            svc.events().delete(calendarId="primary", eventId=eid).execute()
            return outcome.done("calendar_google", note=f"Event {eid} deleted")

        return outcome.failed("calendar_google", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("calendar_google", str(e))
