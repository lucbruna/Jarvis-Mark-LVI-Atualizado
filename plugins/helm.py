"""JARVIS plugin - Kubernetes Helm management."""
from __future__ import annotations

import subprocess
import sys

from core import outcome


PLUGIN = {
    "name": "helm",
    "description": "Manage Helm charts: install, upgrade, uninstall, list, status.",
    "brief": "Helm: install/upgrade/uninstall/list/status.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "install|upgrade|uninstall|list|status|repo_add"},
            "release": {"type": "STRING", "description": "Release name."},
            "chart": {"type": "STRING", "description": "Chart name/path."},
            "namespace": {"type": "STRING", "description": "Namespace (default default)."},
            "values": {"type": "STRING", "description": "Values file path."},
            "repo_name": {"type": "STRING", "description": "Repo name (repo_add)."},
            "repo_url": {"type": "STRING", "description": "Repo URL (repo_add)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _run(cmd):
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0)
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        return proc.returncode, (out + ("\n" + err if err else ""))[:4000]
    except FileNotFoundError:
        return 1, "helm not found on PATH"
    except Exception as e:
        return 1, str(e)


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    ns = params.get("namespace", "default")
    if action == "list":
        code, out = _run(["helm", "list", "-n", ns])
        return outcome.done("helm", note=out[:400], output=out)
    if action == "status":
        code, out = _run(["helm", "status", params.get("release", ""), "-n", ns])
        return outcome.done("helm", note=out[:400], output=out)
    if action == "install":
        cmd = ["helm", "install", params.get("release", ""), params.get("chart", ""), "-n", ns]
        if params.get("values"):
            cmd += ["-f", params["values"]]
        code, out = _run(cmd)
        return (outcome.done if code == 0 else outcome.failed)("helm", note=out[:400], output=out)
    if action == "upgrade":
        cmd = ["helm", "upgrade", params.get("release", ""), params.get("chart", ""), "-n", ns]
        if params.get("values"):
            cmd += ["-f", params["values"]]
        code, out = _run(cmd)
        return (outcome.done if code == 0 else outcome.failed)("helm", note=out[:400], output=out)
    if action == "uninstall":
        code, out = _run(["helm", "uninstall", params.get("release", ""), "-n", ns])
        return (outcome.done if code == 0 else outcome.failed)("helm", note=out[:400], output=out)
    if action == "repo_add":
        code, out = _run(["helm", "repo", "add", params.get("repo_name", ""), params.get("repo_url", "")])
        return (outcome.done if code == 0 else outcome.failed)("helm", note=out[:400], output=out)
    return outcome.failed("helm", f"unknown action: {action}")
