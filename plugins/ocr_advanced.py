"""JARVIS plugin - advanced OCR using Tesseract."""
from __future__ import annotations

from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "ocr_advanced",
    "description": "Extract text from images/PDFs using Tesseract OCR (more accurate than Gemini for scanned docs).",
    "brief": "OCR with Tesseract for images/PDFs.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "file_path": {"type": "STRING", "description": "Path to image or PDF."},
            "language": {"type": "STRING", "description": "OCR language (default eng)."},
        },
        "required": ["file_path"],
    },
    "tier": "extra",
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    params = parameters or {}
    src = Path(params.get("file_path", "")).expanduser()
    if not src.exists():
        return outcome.failed("ocr_advanced", f"file not found: {src}")
    lang = params.get("language", "eng")
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return outcome.failed("ocr_advanced", "pytesseract/Pillow not installed. Run: pip install pytesseract Pillow (and install Tesseract)")
    try:
        if src.suffix.lower() == ".pdf":
            try:
                from pdf2image import convert_from_path
                images = convert_from_path(str(src))
                text = "\n\n".join(pytesseract.image_to_string(img, lang=lang) for img in images)
            except ImportError:
                return outcome.failed("ocr_advanced", "pdf2image not installed for PDF OCR")
        else:
            img = Image.open(src)
            text = pytesseract.image_to_string(img, lang=lang)
        out = src.with_suffix(".txt")
        out.write_text(text, encoding="utf-8")
        msg = f"OCR saved: {out} ({len(text)} chars)"
        if player:
            try: player.write_log(f"JARVIS: {msg}")
            except Exception: pass
        return outcome.done("ocr_advanced", note=msg[:400], text=text[:2000], path=str(out))
    except Exception as e:
        return outcome.failed("ocr_advanced", str(e))
