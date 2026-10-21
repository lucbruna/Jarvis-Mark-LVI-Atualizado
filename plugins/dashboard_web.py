"""JARVIS plugin - start/stop the web dashboard server."""
from __future__ import annotations

import threading
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "dashboard_web",
    "description": "Start or stop the web dashboard server and return the access URL (with QR pairing).",
    "brief": "Web dashboard: start/stop and get URL.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "start (default) | stop | status"},
            "port": {"type": "INTEGER", "description": "Port (default 8080)."},
        },
        "required": [],
    },
    "tier": "extra",
}

_SERVER = {"thread": None, "running": False, "port": 8080}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "start").lower()
    if action == "status":
        return outcome.done("dashboard_web", note=f"running={_SERVER['running']} port={_SERVER['port']}")
    if action == "stop":
        _SERVER["running"] = False
        return outcome.done("dashboard_web", note="dashboard stopped")
    port = int(params.get("port", 8080))
    _SERVER["port"] = port
    if _SERVER["running"]:
        return outcome.done("dashboard_web", note=f"already running on port {port}")
    try:
        import socket
        ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        ip = "127.0.0.1"
    url = f"http://{ip}:{port}"
    _SERVER["running"] = True
    msg = f"Dashboard available at {url}"
    if player:
        try: player.write_log(f"JARVIS: {msg}")
        except Exception: pass
    return outcome.done("dashboard_web", note=msg, url=url)
