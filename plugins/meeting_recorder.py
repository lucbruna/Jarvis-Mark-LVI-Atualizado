"""JARVIS plugin - meeting recorder: record, transcribe, summarize."""
from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path

from core import gemini, outcome


PLUGIN = {
    "name": "meeting_recorder",
    "description": "Records a meeting (audio), transcribes it, and summarizes key points. Uses the microphone and Whisper/Gemini.",
    "brief": "Record, transcribe, and summarize a meeting.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "start|stop|transcribe|summarize"},
            "duration": {"type": "INTEGER", "description": "Recording duration in seconds (start)."},
            "file_path": {"type": "STRING", "description": "Audio file to transcribe/summarize."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}

_RECORDING = {"proc": None, "path": None}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    if action == "start":
        dur = int(params.get("duration", 60))
        out = Path.home() / "Documents" / f"meeting_{int(time.time())}.wav"
        _RECORDING["path"] = out
        # Use ffmpeg to record from default mic
        try:
            proc = subprocess.Popen(
                ["ffmpeg", "-f", "dshow" if sys.platform.startswith("win") else "avfoundation",
                 "-i", "audio=default" if sys.platform.startswith("win") else ":0",
                 "-t", str(dur), "-y", str(out)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0,
            )
            _RECORDING["proc"] = proc
            msg = f"Recording meeting for {dur}s -> {out}"
            if player:
                try: player.write_log(f"JARVIS: {msg}")
                except Exception: pass
            return outcome.done("meeting_recorder", note=msg, path=str(out))
        except FileNotFoundError:
            return outcome.failed("meeting_recorder", "ffmpeg not found. Install ffmpeg.")
        except Exception as e:
            return outcome.failed("meeting_recorder", str(e))

    if action == "stop":
        proc = _RECORDING.get("proc")
        if proc:
            proc.terminate()
            _RECORDING["proc"] = None
        return outcome.done("meeting_recorder", note="Recording stopped")

    if action in ("transcribe", "summarize"):
        src = Path(params.get("file_path") or _RECORDING.get("path", "")).expanduser()
        if not src.exists():
            return outcome.failed("meeting_recorder", f"file not found: {src}")
        # Use file_processor audio transcription via gemini
        try:
            from actions.file_processor import _process_audio
            text = _process_audio(src, "transcribe", {"save": True}, None)
        except Exception as e:
            text = f"Transcription failed: {e}"
        if action == "summarize":
            try:
                resp = gemini.call(f"Summarize this meeting transcript:\n\n{text[:20000]}", tier=gemini.SMART, timeout_ms=60000)
                text = getattr(resp, "text", text) if resp else text
            except Exception:
                pass
        if player:
            try: player.write_log(f"JARVIS: {text[:300]}")
            except Exception: pass
        return outcome.done("meeting_recorder", note=text[:400], text=text)

    return outcome.failed("meeting_recorder", f"unknown action: {action}")
