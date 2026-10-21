"""JARVIS plugin - Dropbox advanced (paper, sharing, webhooks)."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "dropbox_adv",
    "description": "Dropbox advanced: sharing, paper docs, webhooks.",
    "brief": "Dropbox advanced: sharing/paper/webhooks.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "shared_links|paper_docs|webhooks"},
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
        return outcome.failed("dropbox_adv", "Dropbox token not configured")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        if action == "shared_links":
            body = {"path": "", "settings": {"requested_visibility": "public"}}
            req = urllib.request.Request("https://api.dropboxapi.com/2/sharing/list_shared_links", data=json.dumps(body).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            links = data.get("links", [])
            lines = [f"- {l.get('name')}: {l.get('url')}" for l in links]
            return outcome.done("dropbox_adv", note="\n".join(lines) or "no shared links", count=len(links))
        if action == "webhooks":
            req = urllib.request.Request("https://api.dropboxapi.com/2/webhooks/list", data=b"{}", headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            hooks = data.get("webhooks", [])
            lines = [f"- {h.get('id')}: {h.get('url')}" for h in hooks]
            return outcome.done("dropbox_adv", note="\n".join(lines) or "no webhooks", count=len(hooks))
        return outcome.failed("dropbox_adv", f"unknown action: {action}")
    except Exception as e:
        return outcome.failed("dropbox_adv", str(e))
