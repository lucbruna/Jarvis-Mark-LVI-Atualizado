"""JARVIS plugin - VPN control."""
from __future__ import annotations

import subprocess
import sys

from core import outcome


PLUGIN = {
    "name": "vpn_control",
    "description": "Control VPN connections (Windows rasdial, or openvpn/wireguard).",
    "brief": "VPN: connect/disconnect/status.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "connect|disconnect|status|list"},
            "name": {"type": "STRING", "description": "VPN connection name."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _run(cmd):
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0)
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        return proc.returncode, (out + ("\n" + err if err else ""))[:2000]
    except Exception as e:
        return 1, str(e)


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    name = params.get("name", "")
    if sys.platform.startswith("win"):
        if action == "list":
            code, out = _run(["rasdial"])
            return outcome.done("vpn_control", note=out[:500], output=out)
        if action == "connect":
            code, out = _run(["rasdial", name])
            return (outcome.done if code == 0 else outcome.failed)("vpn_control", note=out[:400], output=out)
        if action == "disconnect":
            code, out = _run(["rasdial", name, "/disconnect"])
            return (outcome.done if code == 0 else outcome.failed)("vpn_control", note=out[:400], output=out)
        if action == "status":
            code, out = _run(["rasdial"])
            return outcome.done("vpn_control", note=out[:500], output=out)
    else:
        if action == "list":
            code, out = _run(["nmcli", "connection", "show", "--active"])
            return outcome.done("vpn_control", note=out[:500], output=out)
        if action == "connect":
            code, out = _run(["nmcli", "connection", "up", name])
            return (outcome.done if code == 0 else outcome.failed)("vpn_control", note=out[:400], output=out)
        if action == "disconnect":
            code, out = _run(["nmcli", "connection", "down", name])
            return (outcome.done if code == 0 else outcome.failed)("vpn_control", note=out[:400], output=out)
        if action == "status":
            code, out = _run(["nmcli", "connection", "show", "--active"])
            return outcome.done("vpn_control", note=out[:500], output=out)
    return outcome.failed("vpn_control", f"unknown action: {action}")
