"""JARVIS plugin - backup files/folders to a destination."""
from __future__ import annotations

import shutil
import threading
import time
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "backup",
    "description": "Backup a folder to a destination (zip or copy). Actions: create, list, restore.",
    "brief": "Backup folders (zip/copy).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "create|list"},
            "source": {"type": "STRING", "description": "Source folder."},
            "destination": {"type": "STRING", "description": "Destination folder."},
            "name": {"type": "STRING", "description": "Backup name (optional)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    if action == "create":
        src = Path(params.get("source", str(Path.home() / "Documents"))).expanduser()
        dst = Path(params.get("destination", str(Path.home() / "Backups"))).expanduser()
        dst.mkdir(parents=True, exist_ok=True)
        name = params.get("name") or f"backup_{int(time.time())}"
        archive = dst / name
        try:
            shutil.make_archive(str(archive), "zip", str(src))
            out = archive.with_suffix(".zip")
            msg = f"Backup created: {out}"
            if player:
                try: player.write_log(f"JARVIS: {msg}")
                except Exception: pass
            return outcome.done("backup", note=msg, path=str(out))
        except Exception as e:
            return outcome.failed("backup", str(e))
    if action == "list":
        dst = Path(params.get("destination", str(Path.home() / "Backups"))).expanduser()
        if not dst.exists():
            return outcome.done("backup", note="no backups found")
        files = list(dst.glob("*.zip"))
        lines = [f"- {f.name} ({f.stat().st_size // 1024} KB)" for f in files]
        return outcome.done("backup", note="\n".join(lines) or "no backups", count=len(files))
    return outcome.failed("backup", f"unknown action: {action}")
