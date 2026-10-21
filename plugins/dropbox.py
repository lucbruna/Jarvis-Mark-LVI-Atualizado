"""JARVIS plugin - Dropbox integration."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "dropbox",
    "description": "Dropbox: list, upload, download, delete files.",
    "brief": "Dropbox: list/upload/download/delete.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "list|upload|download|delete"},
            "path": {"type": "STRING", "description": "Remote path (list, default /)."},
            "local_path": {"type": "STRING", "description": "Local file (upload)."},
            "remote_path": {"type": "STRING", "description": "Remote path (upload/download/delete)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _token():
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        return cfg.get("dropbox_token", "")
    except Exception:
        return ""


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    token = _token()
    if not token:
        return outcome.failed("dropbox", "Dropbox token not configured")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        if action == "list":
            path = params.get("path", "")
            body = {"path": path, "recursive": False, "include_media_info": False}
            req = urllib.request.Request("https://api.dropboxapi.com/2/files/list_folder", data=json.dumps(body).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            entries = data.get("entries", [])
            lines = [f"- {e['name']} ({e['.tag']})" for e in entries]
            return outcome.done("dropbox", note="\n".join(lines) or "empty", count=len(entries))
        if action == "upload":
            lp = Path(params.get("local_path", "")).expanduser()
            rp = params.get("remote_path", f"/{lp.name}")
            if not lp.exists():
                return outcome.failed("dropbox", f"file not found: {lp}")
            data = lp.read_bytes()
            req = urllib.request.Request("https://content.dropboxapi.com/2/files/upload", data=data, headers={"Authorization": f"Bearer {token}", "Dropbox-API-Arg": json.dumps({"path": rp, "mode": "add", "autorename": True, "mute": False}), "Content-Type": "application/octet-stream"}, method="POST")
            with urllib.request.urlopen(req, timeout=60) as r:
                res = json.loads(r.read())
            return outcome.done("dropbox", note=f"uploaded: {res.get('id')}")
        if action == "download":
            rp = params.get("remote_path", "")
            req = urllib.request.Request("https://content.dropboxapi.com/2/files/download", headers={"Authorization": f"Bearer {token}", "Dropbox-API-Arg": json.dumps({"path": rp})})
            with urllib.request.urlopen(req, timeout=60) as r:
                content = r.read()
            out = Path.home() / "Downloads" / Path(rp).name
            out.write_bytes(content)
            return outcome.done("dropbox", note=f"downloaded: {out}", path=str(out))
        if action == "delete":
            rp = params.get("remote_path", "")
            body = {"path": rp}
            req = urllib.request.Request("https://api.dropboxapi.com/2/files/delete_v2", data=json.dumps(body).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            return outcome.done("dropbox", note=f"deleted: {rp}")
        return outcome.failed("dropbox", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("dropbox", str(e))
