"""JARVIS plugin - modern STT using SenseVoice if installed, else Whisper.

Provides a transcription action that picks the best available backend.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "stt_modern",
    "description": "Transcribes audio with the best available backend: SenseVoice (if installed) else faster-whisper. Returns text and detected language.",
    "brief": "Modern STT (SenseVoice/Whisper) transcription.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "file_path": {"type": "STRING", "description": "Path to audio file."},
        },
        "required": ["file_path"],
    },
    "tier": "extra",
}


def _sensevoice_available() -> bool:
    try:
        import sensevoice  # noqa
        return True
    except Exception:
        try:
            import funasr  # noqa
            return True
        except Exception:
            return False


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    src = Path(params.get("file_path", "")).expanduser()
    if not src.exists():
        return outcome.failed("stt_modern", f"file not found: {src}")

    # Try SenseVoice via funasr
    if _sensevoice_available():
        try:
            from funasr import AutoModel
            model = AutoModel(model="iic/SenseVoiceSmall", trust_remote_code=True)
            res = model.generate(input=str(src))
            text = res[0].get("text", "") if isinstance(res, list) and res else str(res)
            msg = f"Transcribed (SenseVoice): {text[:500]}"
            if player:
                try: player.write_log(f"JARVIS: {msg}")
                except Exception: pass
            return outcome.done("stt_modern", note=msg, text=text, backend="sensevoice")
        except Exception as e:
            pass

    # Fallback: faster-whisper
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, info = model.transcribe(str(src))
        text = " ".join(s.text for s in segments)
        msg = f"Transcribed (Whisper): {text[:500]}"
        if player:
            try: player.write_log(f"JARVIS: {msg}")
            except Exception: pass
        return outcome.done("stt_modern", note=msg, text=text, backend="whisper", language=getattr(info, "language", ""))
    except ImportError:
        return outcome.failed("stt_modern", "no STT backend installed. Run: pip install faster-whisper")
    except Exception as e:
        return outcome.failed("stt_modern", f"transcription failed: {e}")
