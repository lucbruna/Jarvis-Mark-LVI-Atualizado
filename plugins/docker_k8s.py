"""JARVIS plugin - Docker and Kubernetes management."""
from __future__ import annotations

import subprocess
import sys

from core import outcome


PLUGIN = {
    "name": "docker_k8s",
    "description": "Manage Docker containers and Kubernetes resources. Actions: ps, logs, start, stop, restart, kubectl_get, kubectl_apply.",
    "brief": "Docker/K8s: ps, logs, start/stop, kubectl.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "ps|logs|start|stop|restart|kubectl_get|kubectl_apply"},
            "name": {"type": "STRING", "description": "Container/pod name."},
            "resource": {"type": "STRING", "description": "K8s resource type (pods, svc, deploy)."},
            "file": {"type": "STRING", "description": "YAML file for kubectl_apply."},
            "tail": {"type": "INTEGER", "description": "Log tail lines (default 50)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _run(cmd):
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=120, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0)
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        return proc.returncode, (out + ("\n" + err if err else ""))[:4000]
    except FileNotFoundError:
        return 1, "docker/kubectl not found on PATH"
    except Exception as e:
        return 1, str(e)


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    name = params.get("name", "")
    if action == "ps":
        code, out = _run(["docker", "ps", "--format", "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"])
        return outcome.done("docker_k8s", note=out[:400], output=out)
    if action == "logs":
        tail = str(params.get("tail", 50))
        code, out = _run(["docker", "logs", "--tail", tail, name])
        return outcome.done("docker_k8s", note=out[:400], output=out)
    if action in ("start", "stop", "restart"):
        code, out = _run(["docker", action, name])
        return (outcome.done if code == 0 else outcome.failed)("docker_k8s", note=out[:400], output=out)
    if action == "kubectl_get":
        res = params.get("resource", "pods")
        code, out = _run(["kubectl", "get", res])
        return outcome.done("docker_k8s", note=out[:400], output=out)
    if action == "kubectl_apply":
        f = params.get("file", "")
        code, out = _run(["kubectl", "apply", "-f", f])
        return (outcome.done if code == 0 else outcome.failed)("docker_k8s", note=out[:400], output=out)
    return outcome.failed("docker_k8s", f"unknown action: {action}")
