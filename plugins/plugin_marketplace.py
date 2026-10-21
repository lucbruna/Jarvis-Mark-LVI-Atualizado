"""JARVIS plugin - plugin marketplace: list and install plugins from a repo."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome

PLUGIN = {
    "name": "plugin_marketplace",
    "description": "Browse and install plugins from a community repository. Actions: list, search, install, update.",
    "brief": "Plugin marketplace: browse/install/update plugins.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "list|search|install|update"},
            "query": {"type": "STRING", "description": "Search query (search)."},
            "name": {"type": "STRING", "description": "Plugin name (install/update)."},
            "url": {"type": "STRING", "description": "Plugin file URL (install/update)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}

_REPO_URL = "https://raw.githubusercontent.com/FatihMakes/Mark-LVI-plugins/main/index.json"


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    if action == "list":
        try:
            with urllib.request.urlopen(_REPO_URL, timeout=15) as r:
                idx = json.loads(r.read())
            lines = [f"- {p.get('name')}: {p.get('description', '')}" for p in idx.get("plugins", [])]
            return outcome.done("plugin_marketplace", note="\n".join(lines) or "no plugins", count=len(idx.get("plugins", [])))
        except Exception as e:
            return outcome.failed("plugin_marketplace", f"could not fetch index: {e}")
    if action == "search":
        q = (params.get("query") or "").lower()
        try:
            with urllib.request.urlopen(_REPO_URL, timeout=15) as r:
                idx = json.loads(r.read())
            matches = [p for p in idx.get("plugins", []) if q in p.get("name", "").lower() or q in p.get("description", "").lower()]
            lines = [f"- {p.get('name')}: {p.get('description', '')}" for p in matches]
            return outcome.done("plugin_marketplace", note="\n".join(lines) or "no matches", count=len(matches))
        except Exception as e:
            return outcome.failed("plugin_marketplace", str(e))
    if action == "install":
        url = params.get("url", "")
        name = params.get("name", "")
        if not url:
            return outcome.failed("plugin_marketplace", "url required")
        try:
            dest = Path(__file__).resolve().parents[1] / "plugins" / (f"{name}.py" if name else "downloaded_plugin.py")
            urllib.request.urlretrieve(url, str(dest))
            return outcome.done("plugin_marketplace", note=f"installed: {dest.name}")
        except Exception as e:
            return outcome.failed("plugin_marketplace", str(e))
    if action == "update":
        name = params.get("name", "")
        url = params.get("url", "")
        if not name or not url:
            return outcome.failed("plugin_marketplace", "name and url required")
        try:
            dest = Path(__file__).resolve().parents[1] / "plugins" / f"{name}.py"
            urllib.request.urlretrieve(url, str(dest))
            return outcome.done("plugin_marketplace", note=f"updated: {name}")
        except Exception as e:
            return outcome.failed("plugin_marketplace", str(e))
    return outcome.failed("plugin_marketplace", f"unknown action: {action}")
