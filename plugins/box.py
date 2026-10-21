"""JARVIS plugin - Box integration."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "box",
    "description": "Box: list files, upload, download.",
    "brief": "Box cloud storage.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "list|upload|download"},
            "path": {"type": "STRING", "description": "Folder path (list)."},
            "file_path": {"type": "STRING", "description": "Local file (upload)."},
            "file_id": {"type": "STRING", "description": "File id (download)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _token():
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        return cfg.get("box_access_token", "")
    except Exception:
        return ""


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    token = _token()
    if not token:
        return outcome.failed("box", "Box access token not configured")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        if action == "list":
            folder_id = "0"
            url = f"https://api.box.com/2.0/folders/{folder_id}/items?limit=50"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            entries = data.get("entries", [])
            lines = [f"- {e['name']} ({e['type']})" for e in entries]
            return outcome.done("box", note="\n".join(lines) or "empty", count=len(entries))
        if action == "upload":
            fp = Path(params.get("file_path", "")).expanduser()
            if not fp.exists():
                return outcome.failed("box", f"file not found: {fp}")
            # Simple upload to root
            import urllib.request as u
            boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
            body = []
            body.append(f"--{boundary}")
            body.append(f'Content-Disposition: form-data; name="attributes"')
            body.append("Content-Type: application/json")
            body.append("")
            body.append(json.dumps({"name": fp.name, "parent": {"id": "0"}}))
            body.append(f"--{boundary}")
            body.append(f'Content-Disposition: form-data; name="file"; filename="{fp.name}"')
            body.append("Content-Type: application/octet-stream")
            body.append("")
            body.append(fp.read_bytes().decode("latin-1"))
            body.append(f"--{boundary}--")
            data = "\r\n".join(body).encode("latin-1")
            req = urllib.request.Request("https://upload.box.com/api/2.0/files/content", data=data, headers={"Authorization": f"Bearer {token}", "Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
            with urllib.request.urlopen(req, timeout=60) as r:
                res = json.loads(r.read())
            return outcome.done("box", note=f"uploaded: {res['entries'][0]['id']}")
        if action == "download":
            fid = params.get("file_id", "")
            req = urllib.request.Request(f"https://api.box.com/2.0/files/{fid}/content", headers=headers)
            with urllib.request.urlopen(req, timeout=60) as r:
                content = r.read()
            out = Path.home() / "Downloads" / f"box_{fid}"
            out.write_bytes(content)
            return outcome.done("box", note=f"downloaded: {out}", path=str(out))
        return outcome.failed("box", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("box", str(e))
