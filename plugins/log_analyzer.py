"""JARVIS plugin - log analyzer."""
from __future__ import annotations

import re
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "log_analyzer",
    "description": "Analyze log files: find errors, warnings, count patterns.",
    "brief": "Log analyzer: errors/warnings/patterns.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "file_path": {"type": "STRING", "description": "Path to log file."},
            "pattern": {"type": "STRING", "description": "Pattern to search (regex)."},
            "level": {"type": "STRING", "description": "Filter level: error|warning|info (optional)."},
        },
        "required": ["file_path"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    src = Path(params.get("file_path", "")).expanduser()
    if not src.exists():
        return outcome.failed("log_analyzer", f"file not found: {src}")
    try:
        text = src.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return outcome.failed("log_analyzer", str(e))
    lines = text.splitlines()
    level = (params.get("level") or "").lower()
    pattern = params.get("pattern", "")
    filtered = lines
    if level == "error":
        filtered = [l for l in lines if "error" in l.lower() or "exception" in l.lower() or "fail" in l.lower()]
    elif level == "warning":
        filtered = [l for l in lines if "warn" in l.lower()]
    elif level == "info":
        filtered = [l for l in lines if "info" in l.lower()]
    if pattern:
        try:
            rx = re.compile(pattern, re.IGNORECASE)
            filtered = [l for l in filtered if rx.search(l)]
        except Exception:
            filtered = [l for l in filtered if pattern.lower() in l.lower()]
    # Summary
    errors = sum(1 for l in lines if "error" in l.lower() or "exception" in l.lower())
    warnings = sum(1 for l in lines if "warn" in l.lower())
    msg = f"Total lines: {len(lines)}\nErrors: {errors}\nWarnings: {warnings}\nFiltered: {len(filtered)}"
    if filtered:
        msg += "\n\nTop matches:\n" + "\n".join(filtered[:20])
    if player:
        try: player.write_log(f"JARVIS: {msg[:300]}")
        except Exception: pass
    return outcome.done("log_analyzer", note=msg[:1000], total=len(lines), errors=errors, warnings=warnings, filtered=len(filtered))
