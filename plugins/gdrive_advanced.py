"""JARVIS plugin - Google Drive advanced (search, download, share)."""
from __future__ import annotations

import threading
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "gdrive_advanced",
    "description": "Google Drive: search, download, share files. Requires OAuth.",
    "brief": "Google Drive: search/download/share.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "search|download|share|list"},
            "query": {"type": "STRING", "description": "Search query (search)."},
            "file_id": {"type": "STRING", "description": "File id (download/share)."},
            "destination": {"type": "STRING", "description": "Local destination (download)."},
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
        return None, "Drive not authorized. Run OAuth flow first."
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
        return outcome.failed("gdrive_advanced", err)
    try:
        if action == "search":
            q = params.get("query", "")
            res = svc.files().list(q=f"name contains '{q}'", pageSize=20, fields="files(id,name,mimeType)").execute()
            files = res.get("files", [])
            lines = [f"- {f['name']} ({f['id']})" for f in files]
            return outcome.done("gdrive_advanced", note="\n".join(lines) or "no results", count=len(files))
        if action == "list":
            res = svc.files().list(pageSize=20, fields="files(id,name,mimeType)").execute()
            files = res.get("files", [])
            lines = [f"- {f['name']} ({f['id']})" for f in files]
            return outcome.done("gdrive_advanced", note="\n".join(lines) or "empty", count=len(files))
        if action == "download":
            fid = params.get("file_id", "")
            dest = Path(params.get("destination") or str(Path.home() / "Downloads")).expanduser()
            dest.mkdir(parents=True, exist_ok=True)
            from googleapiclient.http import MediaIoBaseDownload
            import io
            request = svc.files().get_media(fileId=fid)
            fh = io.FileIO(str(dest / f"drive_{fid}"), "wb")
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            fh.close()
            return outcome.done("gdrive_advanced", note=f"downloaded to {dest}")
        if action == "share":
            fid = params.get("file_id", "")
            body = {"role": "reader", "type": "anyone"}
            svc.permissions().create(fileId=fid, body=body).execute()
            res = svc.files().get(fileId=fid, fields="webViewLink").execute()
            return outcome.done("gdrive_advanced", note=f"shared: {res.get('webViewLink')}", link=res.get("webViewLink"))
        return outcome.failed("gdrive_advanced", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("gdrive_advanced", str(e))
