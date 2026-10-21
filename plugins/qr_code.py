"""JARVIS plugin - QR code generator and reader."""
from __future__ import annotations

import threading
import time
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "qr_code",
    "description": "Generate QR codes from text/URLs and read QR codes from images.",
    "brief": "QR code: generate and read.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "generate|read"},
            "data": {"type": "STRING", "description": "Text/URL to encode (generate)."},
            "file_path": {"type": "STRING", "description": "Image file (read)."},
        },
        "required": ["action"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "").lower()
    if action == "generate":
        data = params.get("data", "")
        if not data:
            return outcome.failed("qr_code", "data required")
        try:
            import qrcode
        except ImportError:
            return outcome.failed("qr_code", "qrcode not installed. Run: pip install qrcode[pil]")
        out = Path.home() / "Pictures" / f"qr_{int(time.time())}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        img = qrcode.make(data)
        img.save(out)
        threading.Thread(target=lambda: __import__("subprocess").run(["explorer", "/select,", str(out)] if __import__("sys").platform.startswith("win") else ["open", "-R", str(out)], check=False), daemon=True).start()
        return outcome.done("qr_code", note=f"QR saved: {out}", path=str(out))
    if action == "read":
        src = Path(params.get("file_path", "")).expanduser()
        if not src.exists():
            return outcome.failed("qr_code", f"file not found: {src}")
        try:
            from PIL import Image
            import pyzbar.pyzbar as pyzbar
        except ImportError:
            return outcome.failed("qr_code", "pyzbar/Pillow not installed. Run: pip install pyzbar Pillow")
        try:
            img = Image.open(src)
            decoded = pyzbar.decode(img)
            if not decoded:
                return outcome.failed("qr_code", "no QR code found")
            text = decoded[0].data.decode("utf-8", "replace")
            return outcome.done("qr_code", note=f"QR content: {text}", text=text)
        except Exception as e:
            return outcome.failed("qr_code", str(e))
    return outcome.failed("qr_code", f"unknown action: {action}")
