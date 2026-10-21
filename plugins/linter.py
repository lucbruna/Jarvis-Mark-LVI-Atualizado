"""JARVIS plugin - lint and format code."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "linter",
    "description": "Lint and format code files. Supports Python (black/ruff/flake8), JS/TS (prettier/eslint).",
    "brief": "Lint/format code files.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "file_path": {"type": "STRING", "description": "Path to code file."},
            "action": {"type": "STRING", "description": "format|lint (default format)."},
            "tool": {"type": "STRING", "description": "black|ruff|flake8|prettier (auto if empty)."},
        },
        "required": ["file_path"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    src = Path(params.get("file_path", "")).expanduser()
    if not src.exists():
        return outcome.failed("linter", f"file not found: {src}")
    action = (params.get("action") or "format").lower()
    ext = src.suffix.lower()
    tool = params.get("tool", "")
    if ext == ".py":
        cmd = [sys.executable, "-m", "black", str(src)] if action == "format" else [sys.executable, "-m", "ruff", "check", str(src)]
    elif ext in (".js", ".ts", ".jsx", ".tsx", ".json", ".css", ".html"):
        cmd = ["npx", "prettier", "--write", str(src)] if action == "format" else ["npx", "eslint", str(src)]
    else:
        return outcome.failed("linter", f"unsupported file type: {ext}")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0)
        out = (proc.stdout or "").strip() + (("\n" + (proc.stderr or "").strip()) if proc.stderr else "")
        msg = f"{'Formatted' if action == 'format' else 'Linted'}: {src.name}\n{out[:500]}"
        if player:
            try: player.write_log(f"JARVIS: {msg}")
            except Exception: pass
        return (outcome.done if proc.returncode == 0 else outcome.failed)("linter", note=msg, output=out)
    except FileNotFoundError:
        return outcome.failed("linter", "tool not found on PATH")
    except Exception as e:
        return outcome.failed("linter", str(e))
