"""JARVIS plugin - OneDrive advanced via Microsoft Graph."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "onedrive_advanced",
    "description": "OneDrive: list, download, upload, search files.",
    "brief": "OneDrive: list/download/upload/search.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "list|download|upload|search"},
            "path": {"type": "STRING", "description": "Remote path (list, default /)."},
            "query": {"type": "STRING", "description": "Search query (search)."},
            "file_path": {"type": "STRING", "description": "Local file (upload)."},
            "item_id": {"type": "STRING", "description": "Item id (download)."},
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
        return outcome.failed("onedrive_advanced", err)
    headers = {"Authorization": f"Bearer {token}"}
    try:
        if action == "list":
            path = params.get("path", "/")
            url = f"https://graph.microsoft.com/v1.0/me/drive/root:{path}:/children"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            items = data.get("value", [])
            lines = [f"- {i['name']} ({i['folder']['childCount'] if 'folder' in i else i.get('size', 0)} bytes)" for i in items]
            return outcome.done("onedrive_advanced", note="\n".join(lines) or "empty", count=len(items))
        if action == "search":
            q = params.get("query", "")
            url = f"https://graph.microsoft.com/v1.0/me/drive/search(q='{q}')"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            items = data.get("value", [])
            lines = [f"- {i['name']} ({i['id']})" for i in items[:20]]
            return outcome.done("onedrive_advanced", note="\n".join(lines) or "no results", count=len(items))
        if action == "download":
            iid = params.get("item_id", "")
            url = f"https://graph.microsoft.com/v1.0/me/drive/items/{iid}/content"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as r:
                content = r.read()
            out = Path.home() / "Downloads" / f"onedrive_{iid}"
            out.write_bytes(content)
            return outcome.done("onedrive_advanced", note=f"downloaded: {out}", path=str(out))
        if action == "upload":
            lp = Path(params.get("file_path", "")).expanduser()
            if not lp.exists():
                return outcome.failed("onedrive_advanced", f"file not found: {lp}")
            rp = params.get("remote_path", f"/{lp.name}")
            url = f"https://graph.microsoft.com/v1.0/me/drive/root:{rp}:/content"
            req = urllib.request.Request(url, data=lp.read_bytes(), headers={**headers, "Content-Type": "application/octet-stream"}, method="PUT")
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
            return outcome.done("onedrive_advanced", note=f"uploaded: {data.get('id')}")
        return outcome.failed("onedrive_advanced", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("onedrive_advanced", str(e))
