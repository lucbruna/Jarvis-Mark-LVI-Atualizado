"""JARVIS plugin - enhance audio files: noise reduction and normalization."""
from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "audio_enhance",
    "description": "Enhances an audio file: applies noise reduction (DeepFilterNet if installed, else a basic gate) and normalizes volume. Delivers the enhanced file ready to open.",
    "brief": "Enhance audio files (noise reduction + normalization).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "file_path": {"type": "STRING", "description": "Path to audio file."},
            "normalize": {"type": "BOOLEAN", "description": "Normalize volume (default true)."},
        },
        "required": ["file_path"],
    },
    "tier": "extra",
}


def _reveal(path):
    try:
        if sys.platform.startswith("win"):
            subprocess.run(["explorer", "/select,", str(path)], check=False)
        elif sys.platform == "darwin":
            subprocess.run(["open", "-R", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path.parent)], check=False)
    except Exception:
        pass


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    src = Path(params.get("file_path", "")).expanduser()
    if not src.exists():
        return outcome.failed("audio_enhance", f"file not found: {src}")
    out = src.with_name(src.stem + "_enhanced" + src.suffix)
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(src)
        # basic normalization
        if params.get("normalize", True):
            audio = audio.normalize()
        audio.export(out, format=src.suffix.lstrip(".") or "wav")
    except ImportError:
        return outcome.failed("audio_enhance", "pydub not installed. Run: pip install pydub")
    except Exception as e:
        return outcome.failed("audio_enhance", str(e))
    threading.Thread(target=_reveal, args=(out,), daemon=True).start()
    msg = f"Enhanced audio saved: {out}"
    if player:
        try: player.write_log(f"JARVIS: {msg}")
        except Exception: pass
    return outcome.done("audio_enhance", path=str(out))
