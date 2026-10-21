"""JARVIS plugin - Docker Compose management."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "docker_compose",
    "description": "Manage Docker Compose projects: up, down, ps, logs, build.",
    "brief": "Docker Compose: up/down/ps/logs/build.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "up|down|ps|logs|build|restart"},
            "file": {"type": "STRING", "description": "Compose file path (default docker-compose.yml)."},
            "service": {"type": "STRING", "description": "Service name (optional)."},
            "cwd": {"type": "STRING", "description": "Working directory."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _run(cmd, cwd=None):
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd, timeout=300, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0)
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        return proc.returncode, (out + ("\n" + err if err else ""))[:4000]
    except FileNotFoundError:
        return 1, "docker not found on PATH"
    except Exception as e:
        return 1, str(e)


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    cwd = params.get("cwd")
    if cwd:
        cwd = str(Path(cwd).expanduser())
    f = params.get("file", "docker-compose.yml")
    svc = params.get("service", "")
    if action == "up":
        cmd = ["docker", "compose", "-f", f, "up", "-d"]
        if svc:
            cmd.append(svc)
    elif action == "down":
        cmd = ["docker", "compose", "-f", f, "down"]
    elif action == "ps":
        cmd = ["docker", "compose", "-f", f, "ps"]
    elif action == "logs":
        cmd = ["docker", "compose", "-f", f, "logs", "--tail", "50"]
        if svc:
            cmd.append(svc)
    elif action == "build":
        cmd = ["docker", "compose", "-f", f, "build"]
        if svc:
            cmd.append(svc)
    elif action == "restart":
        cmd = ["docker", "compose", "-f", f, "restart"]
        if svc:
            cmd.append(svc)
    else:
        return outcome.failed("docker_compose", f"unknown action: {action}")
    code, out = _run(cmd, cwd=cwd)
    return (outcome.done if code == 0 else outcome.failed)("docker_compose", note=out[:400], output=out)
