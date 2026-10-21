"""JARVIS plugin - Git/GitHub operations via gh CLI and git."""
from __future__ import annotations

import subprocess
import sys
import threading
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "git_github",
    "description": "Git and GitHub operations: status, commit, push, pull, branch, PR create/list, issue list. Uses git and gh CLI.",
    "brief": "Git/GitHub: status, commit, push, pull, PR, issues.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "status|commit|push|pull|branch|pr_create|pr_list|issue_list|log"},
            "message": {"type": "STRING", "description": "Commit/PR message."},
            "branch": {"type": "STRING", "description": "Branch name."},
            "title": {"type": "STRING", "description": "PR title."},
            "body": {"type": "STRING", "description": "PR body."},
            "cwd": {"type": "STRING", "description": "Working directory."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def _run(cmd, cwd=None):
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              cwd=cwd, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0)
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        return proc.returncode, (out + ("\n" + err if err else ""))[:4000]
    except Exception as e:
        return 1, str(e)


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    cwd = params.get("cwd") or None
    if cwd:
        cwd = str(Path(cwd).expanduser())
    if action == "status":
        code, out = _run(["git", "status", "--short"], cwd=cwd)
        return outcome.done("git_github", note=out or "clean", output=out)
    if action == "log":
        code, out = _run(["git", "log", "--oneline", "-10"], cwd=cwd)
        return outcome.done("git_github", note=out[:400], output=out)
    if action == "commit":
        msg = params.get("message", "update")
        _run(["git", "add", "-A"], cwd=cwd)
        code, out = _run(["git", "commit", "-m", msg], cwd=cwd)
        return (outcome.done if code == 0 else outcome.failed)("git_github", note=out[:400], output=out)
    if action == "push":
        code, out = _run(["git", "push"], cwd=cwd)
        return (outcome.done if code == 0 else outcome.failed)("git_github", note=out[:400], output=out)
    if action == "pull":
        code, out = _run(["git", "pull"], cwd=cwd)
        return (outcome.done if code == 0 else outcome.failed)("git_github", note=out[:400], output=out)
    if action == "branch":
        if params.get("branch"):
            code, out = _run(["git", "checkout", "-b", params["branch"]], cwd=cwd)
        else:
            code, out = _run(["git", "branch", "--show-current"], cwd=cwd)
        return (outcome.done if code == 0 else outcome.failed)("git_github", note=out[:400], output=out)
    if action == "pr_create":
        title = params.get("title", "Update")
        body = params.get("body", "")
        code, out = _run(["gh", "pr", "create", "--title", title, "--body", body], cwd=cwd)
        return (outcome.done if code == 0 else outcome.failed)("git_github", note=out[:400], output=out)
    if action == "pr_list":
        code, out = _run(["gh", "pr", "list"], cwd=cwd)
        return outcome.done("git_github", note=out[:400], output=out)
    if action == "issue_list":
        code, out = _run(["gh", "issue", "list"], cwd=cwd)
        return outcome.done("git_github", note=out[:400], output=out)
    return outcome.failed("git_github", f"unknown action: {action}")
