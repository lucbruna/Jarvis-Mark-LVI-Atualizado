"""JARVIS plugin - text translation via DeepL/Google Translate."""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "translator",
    "description": "Translate text between languages. Uses DeepL if configured, else Google Translate (free).",
    "brief": "Translate text (DeepL/Google).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "text": {"type": "STRING", "description": "Text to translate."},
            "target": {"type": "STRING", "description": "Target language code (e.g. en, pt, tr, es)."},
            "source": {"type": "STRING", "description": "Source language code (auto if empty)."},
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
    # DeepL
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        deepl_key = cfg.get("deepl_api_key", "")
    except Exception:
        deepl_key = ""
    if deepl_key:
        try:
            data = urllib.parse.urlencode({"text": text, "target_lang": target.upper(), "source_lang": source.upper() if source != "auto" else ""}).encode()
            req = urllib.request.Request("https://api-free.deepl.com/v2/translate", data=data, headers={"Authorization": f"DeepL-Auth-Key {deepl_key}"})
            with urllib.request.urlopen(req, timeout=15) as r:
                res = json.loads(r.read())
            translated = res["translations"][0]["text"]
            msg = f"Translation: {translated}"
            if player:
                try: player.write_log(f"JARVIS: {msg}")
                except Exception: pass
            return outcome.done("translator", note=msg, text=translated)
        except Exception as e:
            pass
    # Google Translate (free, unofficial)
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source}&tl={target}&dt=t&q={urllib.parse.quote(text)}"
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.loads(r.read())
        translated = "".join(part[0] for part in data[0] if part[0])
        msg = f"Translation: {translated}"
        if player:
            try: player.write_log(f"JARVIS: {msg}")
            except Exception: pass
        return outcome.done("translator", note=msg, text=translated)
    except Exception as e:
        return outcome.failed("translator", f"translation failed: {e}")
