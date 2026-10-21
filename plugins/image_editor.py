"""JARVIS plugin - image editor: crop, resize, rotate, filters."""
from __future__ import annotations

import threading
import time
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "image_editor",
    "description": "Edit images: crop, resize, rotate, flip, apply filters (grayscale, blur, etc.).",
    "brief": "Image editor: crop/resize/rotate/filter.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "file_path": {"type": "STRING", "description": "Path to image."},
            "action": {"type": "STRING", "description": "crop|resize|rotate|flip|grayscale|blur|sharpen|convert"},
            "width": {"type": "INTEGER", "description": "Width (resize)."},
            "height": {"type": "INTEGER", "description": "Height (resize)."},
            "angle": {"type": "NUMBER", "description": "Rotation angle (rotate)."},
            "left": {"type": "INTEGER", "description": "Crop left."},
            "top": {"type": "INTEGER", "description": "Crop top."},
            "right": {"type": "INTEGER", "description": "Crop right."},
            "bottom": {"type": "INTEGER", "description": "Crop bottom."},
            "format": {"type": "STRING", "description": "Output format (convert)."},
        },
        "required": ["file_path", "action"],
    },
    "tier": "extra",
}


def _reveal(path):
    import subprocess, sys
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
        return outcome.failed("image_editor", f"file not found: {src}")
    try:
        from PIL import Image, ImageFilter, ImageOps
    except ImportError:
        return outcome.failed("image_editor", "Pillow not installed")
    try:
        img = Image.open(src)
        action = params.get("action", "").lower()
        if action == "crop":
            box = (int(params.get("left", 0)), int(params.get("top", 0)), int(params.get("right", img.width)), int(params.get("bottom", img.height)))
            img = img.crop(box)
        elif action == "resize":
            w = int(params.get("width", img.width))
            h = int(params.get("height", img.height))
            img = img.resize((w, h))
        elif action == "rotate":
            img = img.rotate(float(params.get("angle", 90)), expand=True)
        elif action == "flip":
            img = ImageOps.flip(img)
        elif action == "grayscale":
            img = ImageOps.grayscale(img)
        elif action == "blur":
            img = img.filter(ImageFilter.GaussianBlur(radius=2))
        elif action == "sharpen":
            img = img.filter(ImageFilter.SHARPEN)
        elif action == "convert":
            fmt = params.get("format", "png").lower()
            out = src.with_suffix(f".{fmt}")
            img.convert("RGB").save(out)
            threading.Thread(target=_reveal, args=(out,), daemon=True).start()
            return outcome.done("image_editor", note=f"converted: {out}", path=str(out))
        else:
            return outcome.failed("image_editor", f"unknown action: {action}")
        out = src.with_name(src.stem + f"_{action}" + src.suffix)
        img.save(out)
        threading.Thread(target=_reveal, args=(out,), daemon=True).start()
        return outcome.done("image_editor", note=f"edited: {out}", path=str(out))
    except Exception as e:
        return outcome.failed("image_editor", str(e))
