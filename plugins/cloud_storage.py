"""JARVIS plugin - cloud storage (Google Drive, OneDrive, Dropbox)."""
from __future__ import annotations

from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "cloud_storage",
    "description": "Upload/download/list files in cloud storage (Google Drive, OneDrive, Dropbox). Requires API credentials.",
    "brief": "Cloud storage: upload/download/list (Drive/OneDrive/Dropbox).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "provider": {"type": "STRING", "description": "drive|onedrive|dropbox"},
            "action": {"type": "STRING", "description": "upload|download|list"},
            "local_path": {"type": "STRING", "description": "Local file path."},
            "remote_path": {"type": "STRING", "description": "Remote file path/name."},
        },
        "required": ["provider", "action"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    provider = (params.get("provider") or "").lower()
    action = (params.get("action") or "").lower()
    # Google Drive via pydrive2
    if provider == "drive":
        try:
            from pydrive2.auth import GoogleAuth
            from pydrive2.drive import GoogleDrive
            gauth = GoogleAuth()
            gauth.LocalWebserverAuth()
            drive = GoogleDrive(gauth)
            if action == "list":
                files = drive.ListFile({"q": "trashed=false"}).GetList()
                lines = [f"- {f['title']}" for f in files[:20]]
                return outcome.done("cloud_storage", note="\n".join(lines) or "empty", count=len(files))
            if action == "upload":
                lp = params.get("local_path", "")
                f = drive.CreateFile({"title": Path(lp).name})
                f.SetContentFile(lp)
                f.Upload()
                return outcome.done("cloud_storage", note=f"uploaded {lp}")
            return outcome.failed("cloud_storage", f"unknown action: {action}")
        except ImportError:
            return outcome.failed("cloud_storage", "pydrive2 not installed. Run: pip install pydrive2")
        except Exception as e:
            return outcome.failed("cloud_storage", str(e))
    return outcome.failed("cloud_storage", f"provider '{provider}' not implemented yet (use drive)")
