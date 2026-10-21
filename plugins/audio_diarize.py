"""JARVIS plugin - audio diarization (who spoke when)."""
from __future__ import annotations

from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "audio_diarize",
    "description": "Diarize audio: identify speakers and timestamps. Requires pyannote.audio.",
    "brief": "Audio diarization (speakers).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "file_path": {"type": "STRING", "description": "Path to audio file."},
        },
        "required": ["file_path"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    src = Path(params.get("file_path", "")).expanduser()
    if not src.exists():
        return outcome.failed("audio_diarize", f"file not found: {src}")
    try:
        from pyannote.audio import Pipeline
    except ImportError:
        return outcome.failed("audio_diarize", "pyannote.audio not installed. Run: pip install pyannote.audio")
    try:
        pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
        diarization = pipeline(str(src))
        lines = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            lines.append(f"[{turn.start:.1f}s - {turn.end:.1f}s] {speaker}")
        msg = "\n".join(lines[:50])
        return outcome.done("audio_diarize", note=msg[:500], diarization=msg)
    except Exception as e:
        return outcome.failed("audio_diarize", str(e))
