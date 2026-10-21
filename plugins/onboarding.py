"""JARVIS plugin - onboarding wizard for first-time setup."""
from __future__ import annotations

from core import outcome


PLUGIN = {
    "name": "onboarding",
    "description": "Guided first-time setup wizard. Checks configuration and suggests next steps.",
    "brief": "Onboarding wizard for first-time setup.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "check|guide"},
        },
        "required": [],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "check").lower()
    checks = []
    import os
    from pathlib import Path
    base = Path(__file__).resolve().parents[1]
    # Check config
    cfg_path = base / "config" / "api_keys.json"
    if cfg_path.exists():
        try:
            import json
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            if cfg.get("gemini_api_key"):
                checks.append("✓ Gemini API key configured")
            else:
                checks.append("✗ Gemini API key missing")
            if cfg.get("os_system"):
                checks.append(f"✓ OS: {cfg['os_system']}")
        except Exception:
            checks.append("✗ Config file invalid")
    else:
        checks.append("✗ Config file missing")
    # Check providers
    try:
        import importlib.util
        if importlib.util.find_spec("faster_whisper"):
            checks.append("✓ faster-whisper installed")
        else:
            checks.append("○ faster-whisper not installed (optional)")
        if importlib.util.find_spec("piper"):
            checks.append("✓ piper installed")
        else:
            checks.append("○ piper not installed (optional)")
    except Exception:
        pass
    msg = "Onboarding check:\n" + "\n".join(checks)
    if action == "guide":
        msg += "\n\nNext steps: configure API keys in config/api_keys.json, install optional providers from the settings panel."
    if player:
        try: player.write_log(f"JARVIS: {msg}")
        except Exception: pass
    return outcome.done("onboarding", note=msg)
