"""JARVIS plugin - password manager integration (Bitwarden)."""
from __future__ import annotations

import json
import subprocess
import sys

from core import outcome


PLUGIN = {
    "name": "password_manager",
    "description": "Integrate with Bitwarden CLI: list, get, create passwords.",
    "brief": "Password manager (Bitwarden CLI).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "list|get|create|sync"},
            "name": {"type": "STRING", "description": "Item name (get/create)."},
            "username": {"type": "STRING", "description": "Username (create)."},
            "password": {"type": "STRING", "description": "Password (create)."},
            "url": {"type": "STRING", "description": "URL (create)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _run(cmd):
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0)
        return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()
    except FileNotFoundError:
        return 1, "", "bw CLI not found. Install Bitwarden CLI."
    except Exception as e:
        return 1, "", str(e)


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    if action == "list":
        code, out, err = _run(["bw", "list", "items"])
        if code != 0:
            return outcome.failed("password_manager", err or out)
        try:
            items = json.loads(out)
            lines = [f"- {i.get('name')} ({i.get('login', {}).get('username', '')})" for i in items[:20]]
            return outcome.done("password_manager", note="\n".join(lines) or "no items", count=len(items))
        except Exception:
            return outcome.done("password_manager", note=out[:500])
    if action == "get":
        name = params.get("name", "")
        code, out, err = _run(["bw", "get", "item", name])
        if code != 0:
            return outcome.failed("password_manager", err or out)
        try:
            item = json.loads(out)
            login = item.get("login", {})
            msg = f"User: {login.get('username', '')}\nPass: {login.get('password', '')}\nURL: {login.get('uris', [{}])[0].get('uri', '')}"
            return outcome.done("password_manager", note=msg)
        except Exception:
            return outcome.done("password_manager", note=out[:500])
    if action == "create":
        name = params.get("name", "")
        username = params.get("username", "")
        password = params.get("password", "")
        url = params.get("url", "")
        item = {"type": 1, "name": name, "login": {"username": username, "password": password, "uris": [{"uri": url}]}}
        code, out, err = _run(["bw", "create", "item", json.dumps(item)])
        if code != 0:
            return outcome.failed("password_manager", err or out)
        return outcome.done("password_manager", note=f"created: {name}")
    if action == "sync":
        code, out, err = _run(["bw", "sync"])
        return (outcome.done if code == 0 else outcome.failed)("password_manager", note=out or err)
    return outcome.failed("password_manager", f"unknown action: {action}")
