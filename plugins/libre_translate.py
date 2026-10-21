"""JARVIS plugin - LibreTranslate (self-hosted/free translation)."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "libre_translate",
    "description": "Translate text via LibreTranslate (self-hosted or public instance).",
    "brief": "LibreTranslate (self-hosted/free).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "text": {"type": "STRING", "description": "Text to translate."},
            "target": {"type": "STRING", "description": "Target language code."},
            "source": {"type": "STRING", "description": "Source language code (auto if empty)."},
            "url": {"type": "STRING", "description": "LibreTranslate URL (default public instance)."},
        },
        "required": ["text", "target"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    text = params.get("text", "")
    target = params.get("target", "en")
    source = params.get("source", "auto")
    url = params.get("url", "https://libretranslate.com")
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        url = cfg.get("libretranslate_url", url)
    except Exception:
        pass
    try:
        body = {"q": text, "source": source, "target": target, "format": "text"}
        req = urllib.request.Request(f"{url.rstrip('/')}/translate", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        translated = data.get("translatedText", "")
        msg = f"Translation: {translated}"
        if player:
            try: player.write_log(f"JARVIS: {msg}")
            except Exception: pass
        return outcome.done("libre_translate", note=msg, text=translated)
    except Exception as e:
        return outcome.failed("libre_translate", str(e))
