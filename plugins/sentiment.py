"""JARVIS plugin - sentiment analysis of text."""
from __future__ import annotations

from core import gemini, outcome


PLUGIN = {
    "name": "sentiment",
    "description": "Analyze sentiment of text. Returns positive/negative/neutral with score.",
    "brief": "Sentiment analysis of text.",
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
    prompt = f"Analyze the sentiment of this text. Return JSON: {{\"sentiment\": \"positive|negative|neutral\", \"score\": 0.0-1.0, \"reason\": \"...\"}}\n\nText: {text}"
    try:
        resp = gemini.call(prompt, tier=gemini.FAST, timeout_ms=15000)
        raw = getattr(resp, "text", "") if resp else ""
        msg = raw.strip() or "No response"
    except Exception as e:
        msg = f"Failed: {e}"
    if player:
        try: player.write_log(f"JARVIS: {msg[:200]}")
        except Exception: pass
    return outcome.done("sentiment", note=msg[:400], text=msg)
