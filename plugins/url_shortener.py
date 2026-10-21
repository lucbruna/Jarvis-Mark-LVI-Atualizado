"""JARVIS plugin - URL shortener."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "url_shortener",
    "description": "Shorten URLs using TinyURL or is.gd (no API key needed).",
    "brief": "Shorten URLs.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "url": {"type": "STRING", "description": "URL to shorten."},
            "service": {"type": "STRING", "description": "tinyurl (default) or isgd."},
        },
        "required": ["url"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    url = params.get("url", "")
    service = (params.get("service") or "tinyurl").lower()
    try:
        if service == "isgd":
            api = f"https://is.gd/create.php?format=simple&url={urllib.parse.quote(url)}" if False else f"https://is.gd/create.php?format=simple&url={url}"
            import urllib.parse
            api = f"https://is.gd/create.php?format=simple&url={urllib.parse.quote(url)}"
        else:
            import urllib.parse
            api = f"https://tinyurl.com/api-create.php?url={urllib.parse.quote(url)}"
        with urllib.request.urlopen(api, timeout=15) as r:
            short = r.read().decode("utf-8", "replace").strip()
        msg = f"Short URL: {short}"
        if player:
            try: player.write_log(f"JARVIS: {msg}")
            except Exception: pass
        return outcome.done("url_shortener", note=msg, short=short)
    except Exception as e:
        return outcome.failed("url_shortener", str(e))
