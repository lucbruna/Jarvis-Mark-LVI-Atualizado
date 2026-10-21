"""JARVIS plugin - annotated screenshot: capture + draw markers/labels."""
from __future__ import annotations

import threading
import time
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "screenshot_annotate",
    "description": "Capture a screenshot and annotate it with text/markers. Save and open.",
    "brief": "Annotated screenshots.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "text": {"type": "STRING", "description": "Annotation text."},
            "x": {"type": "INTEGER", "description": "X coordinate for marker."},
            "y": {"type": "INTEGER", "description": "Y coordinate for marker."},
        },
        "required": [],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    try:
        from actions.screen_processor import _capture_screen
        img_bytes, mime = _capture_screen()
    except Exception as e:
        return outcome.failed("screenshot_annotate", f"capture failed: {e}")
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io
        img = Image.open(io.BytesIO(img_bytes))
        draw = ImageDraw.Draw(img)
        x = int(params.get("x", 50))
        y = int(params.get("y", 50))
        draw.ellipse([x-10, y-10, x+10, y+10], outline="red", width=3)
        text = params.get("text", "")
        if text:
            draw.text((x + 15, y - 10), text, fill="red")
        out = Path.home() / "Pictures" / f"annotated_{int(time.time())}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(out)
        threading.Thread(target=lambda: __import__("subprocess").run(["explorer", "/select,", str(out)] if __import__("sys").platform.startswith("win") else ["open", "-R", str(out)], check=False), daemon=True).start()
        return outcome.done("screenshot_annotate", note=f"saved: {out}", path=str(out))
    except ImportError:
        return outcome.failed("screenshot_annotate", "Pillow not installed")
    except Exception as e:
        return outcome.failed("screenshot_annotate", str(e))
