"""JARVIS plugin - meme generator."""
from __future__ import annotations

import threading
import time
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "meme_generator",
    "description": "Generate memes with top/bottom text on an image.",
    "brief": "Meme generator (top/bottom text).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "image_path": {"type": "STRING", "description": "Base image path (or empty for default)."},
            "top_text": {"type": "STRING", "description": "Top text."},
            "bottom_text": {"type": "STRING", "description": "Bottom text."},
        },
        "required": [],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return outcome.failed("meme_generator", "Pillow not installed")
    src = params.get("image_path", "")
    if src and Path(src).exists():
        img = Image.open(src)
    else:
        img = Image.new("RGB", (600, 400), color=(50, 50, 50))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except Exception:
        font = ImageFont.load_default()
    top = params.get("top_text", "")
    bottom = params.get("bottom_text", "")
    if top:
        draw.text((10, 10), top.upper(), font=font, fill="white", stroke_width=2, stroke_fill="black")
    if bottom:
        draw.text((10, img.height - 50), bottom.upper(), font=font, fill="white", stroke_width=2, stroke_fill="black")
    out = Path.home() / "Pictures" / f"meme_{int(time.time())}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    threading.Thread(target=lambda: __import__("subprocess").run(["explorer", "/select,", str(out)] if __import__("sys").platform.startswith("win") else ["open", "-R", str(out)], check=False), daemon=True).start()
    return outcome.done("meme_generator", note=f"meme saved: {out}", path=str(out))
