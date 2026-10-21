"""JARVIS plugin - network monitor."""
from __future__ import annotations

import socket
import subprocess
import sys
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "network_monitor",
    "description": "Network diagnostics: ping, DNS lookup, port check, local IP, speed test.",
    "brief": "Network: ping, DNS, port check, IP.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "ping|dns|port|ip|interfaces"},
            "host": {"type": "STRING", "description": "Host (ping/dns/port)."},
            "port": {"type": "INTEGER", "description": "Port (port check)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    if action == "ip":
        try:
            import socket
            ip = socket.gethostbyname(socket.gethostname())
            return outcome.done("network_monitor", note=f"Local IP: {ip}", ip=ip)
        except Exception as e:
            return outcome.failed("network_monitor", str(e))
    if action == "interfaces":
        try:
            import socket
            hostname = socket.gethostname()
            ips = socket.gethostbyname_ex(hostname)[2]
            return outcome.done("network_monitor", note="\n".join(ips), ips=ips)
        except Exception as e:
            return outcome.failed("network_monitor", str(e))
    if action == "dns":
        host = params.get("host", "")
        try:
            ip = socket.gethostbyname(host)
            return outcome.done("network_monitor", note=f"{host} -> {ip}", ip=ip)
        except Exception as e:
            return outcome.failed("network_monitor", str(e))
    if action == "ping":
        host = params.get("host", "8.8.8.8")
        try:
            cmd = ["ping", "-n" if sys.platform.startswith("win") else "-c", "4", host]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0)
            out = (proc.stdout or "").strip()[:500]
            return outcome.done("network_monitor", note=out, output=out)
        except Exception as e:
            return outcome.failed("network_monitor", str(e))
    if action == "port":
        host = params.get("host", "127.0.0.1")
        port = int(params.get("port", 80))
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            result = s.connect_ex((host, port))
            s.close()
            status = "open" if result == 0 else "closed/filtered"
            return outcome.done("network_monitor", note=f"{host}:{port} is {status}", status=status)
        except Exception as e:
            return outcome.failed("network_monitor", str(e))
    return outcome.failed("network_monitor", f"unknown action: {action}")
