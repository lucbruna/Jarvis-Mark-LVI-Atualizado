"""JARVIS plugin - screen recorder via ffmpeg."""
from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "screen_recorder",
    "description": "Record the screen to a video file using ffmpeg. Actions: start, stop.",
    "brief": "Screen recorder (ffmpeg).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "start|stop"},
            "duration": {"type": "INTEGER", "description": "Duration in seconds (start)."},
            "output": {"type": "STRING", "description": "Output file path (optional)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}

_PROC = {"p": None, "path": None}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    if action == "start":
        dur = int(params.get("duration", 60))
        out = Path(params.get("output") or str(Path.home() / "Videos" / f"recording_{int(time.time())}.mp4")).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        _PROC["path"] = out
        try:
            if sys.platform.startswith("win"):
                cmd = ["ffmpeg", "-f", "gdigrab", "-framerate", "30", "-i", "desktop", "-t", str(dur), "-c:v", "libx264", "-preset", "ultrafast", "-y", str(out)]
            elif sys.platform == "darwin":
                cmd = ["ffmpeg", "-f", "avfoundation", "-i", "1", "-t", str(dur), "-y", str(out)]
            else:
                cmd = ["ffmpeg", "-f", "x11grab", "-r", "30", "-i", ":0.0", "-t", str(dur), "-y", str(out)]
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0)
            _PROC["p"] = proc
            msg = f"Recording screen for {dur}s -> {out}"
            if player:
                try: player.write_log(f"JARVIS: {msg}")
                except Exception: pass
            return outcome.done("screen_recorder", note=msg, path=str(out))
        except FileNotFoundError:
            return outcome.failed("screen_recorder", "ffmpeg not found")
        except Exception as e:
            return outcome.failed("screen_recorder", str(e))
    if action == "stop":
        p = _PROC.get("p")
        if p:
            p.terminate()
            _PROC["p"] = None
        path = _PROC.get("path")
        return outcome.done("screen_recorder", note=f"Recording stopped. File: {path}")
    return outcome.failed("screen_recorder", f"unknown action: {action}")
