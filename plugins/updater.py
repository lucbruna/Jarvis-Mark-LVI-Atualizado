"""JARVIS plugin - check for app updates from GitHub releases."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from urllib.request import urlopen

from core import outcome

PLUGIN = {
    "name": "updater",
    "description": "Checks GitHub for a newer Mark LVI release and reports the download link. Use for 'check for updates', 'is there a new version'.",
    "brief": "Checks GitHub releases for a newer app version.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "repo": {"type": "STRING", "description": "GitHub repo (default: FatihMakes/Mark-LVI)."},
        },
        "required": [],
    },
    "tier": "extra",
}

_REPO = "FatihMakes/Mark-LVI"


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    repo = (params.get("repo") or _REPO).strip()
    try:
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        with urlopen(url, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        tag = data.get("tag_name", "")
        html = data.get("html_url", "")
        msg = f"Latest release: {tag}\n{html}"
        if player:
            try:
                player.write_log(f"JARVIS: {msg}")
            except Exception:
                pass
        return outcome.done("updater", note=msg[:400], tag=tag, url=html)
    except Exception as e:
        return outcome.failed("updater", f"update check failed: {e}")
