"""JARVIS plugin - clone a voice with ElevenLabs from an audio sample.

Uses ElevenLabs Instant Voice Cloning API. Requires an API key with cloning
permission. The cloned voice id is stored and can be used by tts_elevenlabs.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

from core import outcome

PLUGIN = {
    "name": "voice_clone",
    "description": "Clones a voice from an audio sample using ElevenLabs Instant Voice Cloning. Provide an audio file. Returns a voice_id to use with ElevenLabs TTS.",
    "brief": "Clone a voice (ElevenLabs) from an audio sample.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "audio_path": {"type": "STRING", "description": "Path to audio sample (mp3/wav)."},
            "name": {"type": "STRING", "description": "Name for the cloned voice."},
        },
        "required": ["audio_path"],
    },
    "tier": "extra",
}


def _api_key() -> str:
    try:
        cfg = json.loads(Path(__file__).resolve().parents[1].joinpath("config", "api_keys.json").read_text(encoding="utf-8"))
        return os.environ.get("ELEVENLABS_API_KEY") or cfg.get("elevenlabs_api_key") or ""
    except Exception:
        return os.environ.get("ELEVENLABS_API_KEY", "")


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    audio_path = Path(params.get("audio_path", "")).expanduser()
    if not audio_path.exists():
        return outcome.failed("voice_clone", f"file not found: {audio_path}")
    key = _api_key()
    if not key:
        return outcome.failed("voice_clone", "ElevenLabs API key not configured")
    name = params.get("name") or f"cloned_{int(time.time())}"
    try:
        import httpx
        with open(audio_path, "rb") as f:
            files = {"files": (audio_path.name, f, "audio/mpeg")}
            data = {"name": name}
            with httpx.Client(timeout=120.0) as cl:
                r = cl.post("https://api.elevenlabs.io/v1/voices/add",
                            headers={"xi-api-key": key}, data=data, files=files)
                r.raise_for_status()
                voice_id = r.json().get("voice_id", "")
        msg = f"Voice cloned: {name} (id={voice_id})"
        if player:
            try: player.write_log(f"JARVIS: {msg}")
            except Exception: pass
        return outcome.done("voice_clone", note=msg, voice_id=voice_id)
    except Exception as e:
        return outcome.failed("voice_clone", f"clone failed: {e}")
