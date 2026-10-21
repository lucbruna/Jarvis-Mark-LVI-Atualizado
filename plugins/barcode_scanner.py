"""JARVIS plugin - barcode scanner via camera or image."""
from __future__ import annotations

from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "barcode_scanner",
    "description": "Read barcodes from an image file using pyzbar.",
    "brief": "Barcode scanner from image.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "file_path": {"type": "STRING", "description": "Path to image containing barcode."},
        },
        "required": ["file_path"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    src = Path(params.get("file_path", "")).expanduser()
    if not src.exists():
        return outcome.failed("barcode_scanner", f"file not found: {src}")
    try:
        from PIL import Image
        import pyzbar.pyzbar as pyzbar
    except ImportError:
        return outcome.failed("barcode_scanner", "pyzbar/Pillow not installed")
    try:
        img = Image.open(src)
        decoded = pyzbar.decode(img)
        if not decoded:
            return outcome.failed("barcode_scanner", "no barcode found")
        results = [{"type": d.type, "data": d.data.decode("utf-8", "replace")} for d in decoded]
        msg = "\n".join(f"{r['type']}: {r['data']}" for r in results)
        return outcome.done("barcode_scanner", note=msg, results=results)
    except Exception as e:
        return outcome.failed("barcode_scanner", str(e))
