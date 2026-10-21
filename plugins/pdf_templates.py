"""JARVIS plugin - generate PDF documents from templates."""
from __future__ import annotations

import threading
import time
from pathlib import Path

from core import outcome


PLUGIN = {
    "name": "pdf_templates",
    "description": "Generate PDF documents (invoice, report, letter) from structured data. Uses reportlab if installed.",
    "brief": "Generate PDFs from templates (invoice/report/letter).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "template": {"type": "STRING", "description": "invoice|report|letter"},
            "title": {"type": "STRING", "description": "Document title."},
            "content": {"type": "STRING", "description": "Body text or JSON data."},
            "output": {"type": "STRING", "description": "Output file path (default: documents)."},
        },
        "required": ["template", "title"],
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
    template = (params.get("template") or "report").lower()
    title = params.get("title", "Document")
    content = params.get("content", "")
    out_dir = Path(params.get("output") or str(Path.home() / "Documents")).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{title.replace(' ', '_')}_{int(time.time())}.pdf"

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError:
        return outcome.failed("pdf_templates", "reportlab not installed. Run: pip install reportlab")

    try:
        c = canvas.Canvas(str(out), pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, 750, title)
        c.setFont("Helvetica", 11)
        y = 720
        for line in content.split("\n"):
            c.drawString(72, y, line[:100])
            y -= 14
            if y < 72:
                c.showPage()
                y = 750
        c.save()
    except Exception as e:
        return outcome.failed("pdf_templates", str(e))

    threading.Thread(target=_reveal, args=(out,), daemon=True).start()
    msg = f"PDF saved: {out}"
    if player:
        try: player.write_log(f"JARVIS: {msg}")
        except Exception: pass
    return outcome.done("pdf_templates", note=msg, path=str(out))
