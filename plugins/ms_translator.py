"""JARVIS plugin - Microsoft Translator."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "ms_translator",
    "description": "Translate text via Microsoft Azure Translator.",
    "brief": "Microsoft Translator.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "text": {"type": "STRING", "description": "Text to translate."},
            "target": {"type": "STRING", "description": "Target language code."},
            "source": {"type": "STRING", "description": "Source language code (auto if empty)."},
        },
        "required": ["text", "target"],
    },
    "tier": "extra",
}


def _key():
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        return cfg.get("azure_translator_key", ""), cfg.get("azure_translator_region", "global")
    except Exception:
        return "", "global"


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    text = params.get("text", "")
    target = params.get("target", "en")
    source = params.get("source", "")
    key, region = _key()
    if not key:
        return outcome.failed("ms_translator", "Azure Translator key not configured")
    try:
        body = [{"text": text}]
        url = f"https://api.cognitive.microsofttranslator.com/translate?api-version=3.0&to={target}"
        if source:
            url += f"&from={source}"
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Ocp-Apim-Subscription-Key": key, "Ocp-Apim-Subscription-Region": region, "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        translated = data[0]["translations"][0]["text"]
        msg = f"Translation: {translated}"
        if player:
            try: player.write_log(f"JARVIS: {msg}")
            except Exception: pass
        return outcome.done("ms_translator", note=msg, text=translated)
    except Exception as e:
        return outcome.failed("ms_translator", str(e))
