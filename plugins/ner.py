"""JARVIS plugin - named entity recognition (NER)."""
from __future__ import annotations

from core import gemini, outcome


PLUGIN = {
    "name": "ner",
    "description": "Extract named entities (people, places, orgs, dates) from text.",
    "brief": "Named entity recognition.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "text": {"type": "STRING", "description": "Text to analyze."},
        },
        "required": ["text"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    text = params.get("text", "")
    prompt = f"Extract named entities from this text. Return JSON array of {{\"entity\": \"...\", \"type\": \"person|place|org|date|other\"}}.\n\nText: {text}"
    try:
        resp = gemini.call(prompt, tier=gemini.FAST, timeout_ms=20000)
        raw = getattr(resp, "text", "[]") if resp else "[]"
    except Exception as e:
        raw = f"Failed: {e}"
    if player:
        try: player.write_log(f"JARVIS: {raw[:200]}")
        except Exception: pass
    return outcome.done("ner", note=raw[:400], entities=raw)
