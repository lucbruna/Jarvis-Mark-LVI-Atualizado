"""JARVIS plugin - git blame and history."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "git_blame",
    "description": "Git blame and file history. Actions: blame, history, diff.",
    "brief": "Git blame/history/diff.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "blame|history|diff"},
            "file": {"type": "STRING", "description": "File path."},
            "lines": {"type": "STRING", "description": "Line range for blame (e.g. 10,20)."},
            "cwd": {"type": "STRING", "description": "Working directory."},
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
    cwd = params.get("cwd")
    if cwd:
        cwd = str(Path(cwd).expanduser())
    f = params.get("file", "")
    if action == "blame":
        cmd = ["git", "blame", f]
        if params.get("lines"):
            cmd += ["-L", params["lines"]]
        code, out = _run(cmd, cwd=cwd)
        return outcome.done("git_blame", note=out[:500], output=out)
    if action == "history":
        code, out = _run(["git", "log", "--oneline", "--", f], cwd=cwd)
        return outcome.done("git_blame", note=out[:500], output=out)
    if action == "diff":
        code, out = _run(["git", "diff", "HEAD", "--", f], cwd=cwd)
        return outcome.done("git_blame", note=out[:500], output=out)
    return outcome.failed("git_blame", f"unknown action: {action}")
