"""JARVIS plugin - trigger GitHub Actions workflows."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "github_actions",
    "description": "Trigger GitHub Actions workflows and check run status. Uses gh CLI.",
    "brief": "GitHub Actions: trigger/check runs.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "trigger|list|status"},
            "workflow": {"type": "STRING", "description": "Workflow file name (trigger)."},
            "branch": {"type": "STRING", "description": "Branch (trigger)."},
            "repo": {"type": "STRING", "description": "owner/repo (optional)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _run(cmd, cwd=None):
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0)
        return proc.returncode, ((proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")).strip()[:4000]
    except Exception as e:
        return 1, str(e)


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    repo = params.get("repo", "")
    if action == "trigger":
        wf = params.get("workflow", "")
        branch = params.get("branch", "main")
        cmd = ["gh", "workflow", "run", wf, "--ref", branch]
        if repo:
            cmd += ["-R", repo]
        code, out = _run(cmd)
        return (outcome.done if code == 0 else outcome.failed)("github_actions", note=out[:400], output=out)
    if action == "list":
        cmd = ["gh", "run", "list"]
        if repo:
            cmd += ["-R", repo]
        code, out = _run(cmd)
        return outcome.done("github_actions", note=out[:400], output=out)
    if action == "status":
        cmd = ["gh", "run", "view"]
        if repo:
            cmd += ["-R", repo]
        code, out = _run(cmd)
        return outcome.done("github_actions", note=out[:400], output=out)
    return outcome.failed("github_actions", f"unknown action: {action}")
