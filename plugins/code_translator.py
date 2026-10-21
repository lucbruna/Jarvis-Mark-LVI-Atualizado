"""JARVIS plugin - translate code between languages."""
from __future__ import annotations

from core import gemini, outcome


PLUGIN = {
    "name": "code_translator",
    "description": "Translate code from one programming language to another.",
    "brief": "Translate code between languages.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "code": {"type": "STRING", "description": "Source code."},
            "from_lang": {"type": "STRING", "description": "Source language."},
            "to_lang": {"type": "STRING", "description": "Target language."},
        },
        "required": ["code", "to_lang"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    code = params.get("code", "")
    from_lang = params.get("from_lang", "auto")
    to_lang = params.get("to_lang", "")
    prompt = f"Translate this {from_lang} code to {to_lang}. Return only the code in a fenced block.\n\n```{from_lang}\n{code}\n```"
    try:
        resp = gemini.call(prompt, tier=gemini.SMART, timeout_ms=45000)
        text = getattr(resp, "text", "No response") if resp else "No response"
    except Exception as e:
        text = f"Failed: {e}"
    if player:
        try: player.write_log(f"JARVIS: {text[:200]}")
        except Exception: pass
    return outcome.done("code_translator", note=text[:500], code=text)
